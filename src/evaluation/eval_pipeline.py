import re
from typing import Dict, List
from pydantic import BaseModel, Field

from src.agent.workflow import LiteratureReviewAgent
from src.indexing.citation_graph import CitationGraphStore
from src.indexing.vector_store import HybridVectorStore, tokenize_scientific_text
from src.models.schemas import SynthesisResponse
from src.retrieval.hybrid_retriever import HybridGraphRetriever


class EvalSample(BaseModel):
    """A benchmark question with expected ground-truth paper IDs and key technical terms."""

    question: str
    expected_paper_ids: List[str] = Field(default_factory=list)
    expected_keywords: List[str] = Field(default_factory=list)


class EvalMetrics(BaseModel):
    """Quantitative RAG evaluation metrics inspired by Ragas."""

    question: str
    context_precision: float
    context_recall: float
    citation_faithfulness: float
    answer_relevance: float


DEFAULT_BENCHMARK_SAMPLES: List[EvalSample] = [
    EvalSample(
        question="How does QLoRA reduce memory usage using 4-bit NormalFloat and Double Quantization?",
        expected_paper_ids=["2305.14314"],
        expected_keywords=["4-bit", "NormalFloat", "NF4", "double", "quantization", "memory"],
    ),
    EvalSample(
        question="What are the main innovations of QLoRA and how does Guanaco perform on benchmarks?",
        expected_paper_ids=["2305.14314"],
        expected_keywords=["Guanaco", "paged", "optimizers", "benchmark", "finetuning"],
    ),
    EvalSample(
        question="Compare parameter-efficient finetuning methods and memory footprint across quantized models",
        expected_paper_ids=["2305.14314", "2506.20629"],
        expected_keywords=["LoRA", "quantization", "parameters", "memory", "adapter"],
    ),
]


def build_dynamic_benchmark(
    vector_store: HybridVectorStore,
    max_samples: int = 5,
) -> List[EvalSample]:
    """
    Dynamically generate benchmark samples from whatever papers are currently indexed
    in the vector store, so Evaluation works on ANY research topic (Robotics, CV, Bio, RAG, etc.).
    """
    if not vector_store.chunks_by_id:
        return DEFAULT_BENCHMARK_SAMPLES

    papers_seen: Dict[str, List] = {}
    for chunk in vector_store.chunks_by_id.values():
        papers_seen.setdefault(chunk.paper_id, []).append(chunk)

    samples: List[EvalSample] = []
    STOPWORDS = {
        "the", "and", "for", "with", "that", "this", "from", "are", "was", "were",
        "can", "our", "we", "in", "of", "to", "on", "by", "as", "is", "at", "an",
        "abstract", "introduction", "method", "methodology", "experiments", "conclusion",
    }

    for pid, chunks in list(papers_seen.items())[:max_samples]:
        title = chunks[0].paper_title
        # Extract distinctive keywords from the paper title and first chunk
        title_tokens = [
            tok for tok in tokenize_scientific_text(title)
            if len(tok) >= 4 and tok not in STOPWORDS
        ]
        keywords = list(dict.fromkeys(title_tokens))[:6]
        samples.append(
            EvalSample(
                question=f"What are the main methodology, architecture, and key findings of '{title}'?",
                expected_paper_ids=[pid],
                expected_keywords=keywords,
            )
        )

    if len(papers_seen) >= 2:
        pids = list(papers_seen.keys())[:2]
        t1 = papers_seen[pids[0]][0].paper_title
        t2 = papers_seen[pids[1]][0].paper_title
        kw1 = [t for t in tokenize_scientific_text(t1) if len(t) >= 4 and t not in STOPWORDS][:3]
        kw2 = [t for t in tokenize_scientific_text(t2) if len(t) >= 4 and t not in STOPWORDS][:3]
        samples.append(
            EvalSample(
                question=f"Compare the approaches and contributions of '{t1}' versus '{t2}'.",
                expected_paper_ids=pids,
                expected_keywords=list(dict.fromkeys(kw1 + kw2)),
            )
        )

    return samples or DEFAULT_BENCHMARK_SAMPLES


class RAGEvaluator:
    """
    Evaluates the Literature Review Assistant across 4 core RAG metrics:
    1. Context Precision: Fraction of retrieved chunks belonging to expected ground-truth papers.
    2. Context Recall: Fraction of expected ground-truth papers & keywords covered in retrieved chunks.
    3. Citation Faithfulness: Fraction of inline citations in the answer backed by retrieved chunks.
    4. Answer Relevance: Coverage of query & expected technical concepts in the synthesized answer.
    """

    @staticmethod
    def evaluate_response(sample: EvalSample, response: SynthesisResponse) -> EvalMetrics:
        retrieved_paper_ids = [p.chunk.paper_id for p in response.citations]
        expected_set = set(sample.expected_paper_ids)

        # 1. Context Precision
        if retrieved_paper_ids and expected_set:
            relevant_chunks = sum(1 for pid in retrieved_paper_ids if pid in expected_set)
            context_precision = relevant_chunks / len(retrieved_paper_ids)
        else:
            context_precision = 0.0

        # 2. Context Recall (paper coverage + keyword coverage in retrieved context)
        if expected_set:
            paper_recall = len(expected_set & set(retrieved_paper_ids)) / len(expected_set)
        else:
            paper_recall = 1.0

        full_context_text = " ".join(p.chunk.content.lower() for p in response.citations)
        full_context_tokens = set(tokenize_scientific_text(full_context_text))
        if sample.expected_keywords:
            kw_hits = sum(
                1
                for kw in sample.expected_keywords
                if kw.lower() in full_context_tokens or kw.lower() in full_context_text
            )
            kw_recall = kw_hits / len(sample.expected_keywords)
        else:
            kw_recall = 1.0
        context_recall = 0.5 * paper_recall + 0.5 * kw_recall

        # 3. Citation Faithfulness & Evidence Grounding (COR-11)
        valid_ids = set(retrieved_paper_ids)
        cited_ids = re.findall(r"\[([0-9]{4}\.[0-9]{4,5}|[A-Za-z0-9_.\-]+):", response.answer)
        if cited_ids:
            id_validity = sum(1 for cid in cited_ids if cid in valid_ids) / len(cited_ids)
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", response.answer) if "[" in s]
            overlaps = []
            for s in sentences:
                s_cids = re.findall(r"\[([0-9]{4}\.[0-9]{4,5}|[A-Za-z0-9_.\-]+):", s)
                if not s_cids:
                    continue
                s_tokens = set(tokenize_scientific_text(s.lower()))
                target_content = " ".join(p.chunk.content.lower() for p in response.citations if p.chunk.paper_id in s_cids)
                target_tokens = set(tokenize_scientific_text(target_content))
                shared = len(s_tokens & target_tokens)
                overlaps.append(min(1.0, (shared / max(len(s_tokens), 1)) * 1.5))
            text_support = (sum(overlaps) / len(overlaps)) if overlaps else id_validity
            citation_faithfulness = 0.5 * id_validity + 0.5 * text_support
        else:
            citation_faithfulness = 0.0

        # 4. Answer Relevance
        q_tokens = set(tokenize_scientific_text(sample.question))
        ans_tokens = set(tokenize_scientific_text(response.answer))
        q_overlap = len(q_tokens & ans_tokens) / max(len(q_tokens), 1)
        if sample.expected_keywords:
            ans_kw_hits = sum(
                1 for kw in sample.expected_keywords if kw.lower() in response.answer.lower()
            )
            ans_kw_score = ans_kw_hits / len(sample.expected_keywords)
            answer_relevance = 0.4 * q_overlap + 0.6 * ans_kw_score
        else:
            answer_relevance = q_overlap

        return EvalMetrics(
            question=sample.question,
            context_precision=round(context_precision, 3),
            context_recall=round(context_recall, 3),
            citation_faithfulness=round(citation_faithfulness, 3),
            answer_relevance=round(answer_relevance, 3),
        )

    def run_benchmark(
        self,
        agent: LiteratureReviewAgent,
        samples: List[EvalSample],
    ) -> Dict[str, object]:
        """Run evaluation across a list of benchmark samples and compute aggregate scores."""
        per_sample: List[EvalMetrics] = []
        for sample in samples:
            resp = agent.run(sample.question)
            metrics = self.evaluate_response(sample, resp)
            per_sample.append(metrics)

        n = max(len(per_sample), 1)
        summary = {
            "num_samples": len(per_sample),
            "mean_context_precision": round(sum(m.context_precision for m in per_sample) / n, 3),
            "mean_context_recall": round(sum(m.context_recall for m in per_sample) / n, 3),
            "mean_citation_faithfulness": round(sum(m.citation_faithfulness for m in per_sample) / n, 3),
            "mean_answer_relevance": round(sum(m.answer_relevance for m in per_sample) / n, 3),
            "details": [m.model_dump() for m in per_sample],
        }
        return summary

    def run_ablation_study(
        self,
        vector_store: HybridVectorStore,
        citation_graph: CitationGraphStore,
        samples: List[EvalSample] | None = None,
    ) -> Dict[str, Dict[str, object]]:
        """
        Compare 3 retrieval modes side-by-side on the same benchmark:
        1. 'dense': Dense Vector Search only
        2. 'sparse': BM25 Lexical Search only
        3. 'hybrid': Hybrid (Qdrant + BM25 via RRF) + Reranking
        """
        active_samples = samples or build_dynamic_benchmark(vector_store)
        results: Dict[str, Dict[str, object]] = {}
        for mode in ("dense", "sparse", "hybrid"):
            retriever = HybridGraphRetriever(
                vector_store=vector_store,
                citation_graph=citation_graph,
                search_mode=mode,
            )
            agent = LiteratureReviewAgent(retriever=retriever)
            results[mode] = self.run_benchmark(agent=agent, samples=active_samples)
        return results
