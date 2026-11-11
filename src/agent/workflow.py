import time
from typing import Dict, Iterator, Optional

from src.agent.nodes import AgentNodes, LLMClient
from src.agent.state import ResearchAgentState
from src.models.schemas import RetrievedPassage, SynthesisResponse
from src.retrieval.hybrid_retriever import HybridGraphRetriever


def passage_to_dict(p: RetrievedPassage) -> Dict:
    """Public JSON representation of a retrieved passage."""
    return {
        "citation_tag": p.citation_tag,
        "paper_id": p.chunk.paper_id,
        "paper_title": p.chunk.paper_title,
        "section_title": p.chunk.section_title,
        "page_numbers": p.chunk.page_numbers,
        "content": p.chunk.content,
        "rerank_score": round(p.rerank_score, 4),
        "dense_score": round(p.dense_score, 4),
        "sparse_score": round(p.sparse_score, 4),
    }


class LiteratureReviewAgent:
    """
    Agentic RAG workflow orchestrating:
    1. Query Decomposition (Single vs. Multi-paper comparative queries)
    2. Multi-Query Hybrid & Citation Graph Retrieval + Cross-Encoder Reranking
    3. Grounded Literature Synthesis with section-level citations
    4. Hallucination & Citation Verification Guard
    """

    def __init__(
        self,
        retriever: HybridGraphRetriever,
        llm_client: Optional[LLMClient] = None,
    ):
        self.nodes = AgentNodes(retriever=retriever, llm_client=llm_client)

    def run(
        self,
        question: str,
        language: str = "vi",
        paper_id_filter: Optional[str] = None,
    ) -> SynthesisResponse:
        """Execute the 4-stage Agentic RAG pipeline and return a structured SynthesisResponse."""
        state: ResearchAgentState = {
            "question": question,
            "language": language,
            "paper_id_filter": paper_id_filter,
        }

        state = self.nodes.decompose_query(state)
        state = self.nodes.retrieve_evidence(state)
        state = self.nodes.synthesize_answer(state)
        state = self.nodes.verify_grounding(state)

        return SynthesisResponse(
            question=question,
            sub_queries=state.get("sub_queries", [question]),
            answer=state.get("draft_answer", ""),
            citations=state.get("retrieved_passages", []),
            related_papers_from_graph=state.get("related_papers_from_graph", []),
            is_grounded=state.get("is_grounded", False),
        )

    def run_stream(
        self,
        question: str,
        language: str = "vi",
        paper_id_filter: Optional[str] = None,
    ) -> Iterator[Dict]:
        """
        Streaming pipeline. Event order:
          status -> sources -> (thinking | token)* | fallback -> done
        Sources are sent BEFORE the LLM starts, so the UI can show them immediately.
        """
        t_start = time.perf_counter()
        state: ResearchAgentState = {
            "question": question,
            "language": language,
            "paper_id_filter": paper_id_filter,
        }

        yield {"type": "status", "stage": "retrieval", "message": "Searching sources (Hybrid + Cross-Encoder)..."}
        state = self.nodes.decompose_query(state)
        state = self.nodes.retrieve_evidence(state)
        retrieval_ms = round((time.perf_counter() - t_start) * 1000)

        yield {
            "type": "sources",
            "sub_queries": state.get("sub_queries", [question]),
            "citations": [passage_to_dict(p) for p in state.get("retrieved_passages", [])],
            "related_papers_from_graph": state.get("related_papers_from_graph", []),
            "retrieval_ms": retrieval_ms,
        }

        yield {"type": "status", "stage": "generation", "message": "Waiting for the model's first token..."}
        for event in self.nodes.synthesize_answer_stream(state):
            yield event

        state = self.nodes.verify_grounding(state)
        yield {
            "type": "done",
            "answer": state.get("draft_answer", ""),
            "is_grounded": state.get("is_grounded", False),
            "grounding_score": state.get("grounding_score", 0.0),
            "is_partial": state.get("is_partial", False),
            "timings": {
                "retrieval_ms": retrieval_ms,
                "ttft_ms": state.get("ttft_ms"),
                "llm_ms": state.get("llm_ms"),
                "total_ms": round((time.perf_counter() - t_start) * 1000),
            },
        }
