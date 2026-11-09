from pathlib import Path

from src.agent.nodes import LLMClient
from src.agent.workflow import LiteratureReviewAgent
from src.evaluation.eval_pipeline import EvalSample, RAGEvaluator
from src.indexing.citation_graph import CitationGraphStore
from src.indexing.vector_store import HashingEmbedder, HybridVectorStore
from src.models.schemas import PaperMetadata, SectionChunk
from src.retrieval.hybrid_retriever import HybridGraphRetriever
from src.retrieval.reranker import CrossEncoderReranker


def build_mock_literature_agent(tmp_path: Path) -> LiteratureReviewAgent:
    vector_store = HybridVectorStore(
        embedder=HashingEmbedder(dimension=128),
        collection_name="test_agent_collection",
        in_memory=True,
    )
    citation_graph = CitationGraphStore(graph_path=tmp_path / "graph.json")

    citation_graph.add_paper(
        PaperMetadata(
            paper_id="2106.09685",
            title="LoRA: Low-Rank Adaptation of Large Language Models",
            references=["W_TRANSFORMER"],
        )
    )
    citation_graph.add_paper(
        PaperMetadata(
            paper_id="2305.14314",
            title="QLoRA: Efficient Finetuning of Quantized LLMs",
            references=["2106.09685", "W_TRANSFORMER"],
        )
    )

    vector_store.index_chunks(
        [
            SectionChunk(
                chunk_id="2106.09685_sec1_0",
                paper_id="2106.09685",
                paper_title="LoRA: Low-Rank Adaptation of Large Language Models",
                section_title="2 Low-Rank Parametrization",
                page_numbers=[2],
                content="LoRA freezes the pretrained model weights and injects trainable rank decomposition matrices into each layer of the Transformer architecture.",
            ),
            SectionChunk(
                chunk_id="2305.14314_sec1_0",
                paper_id="2305.14314",
                paper_title="QLoRA: Efficient Finetuning of Quantized LLMs",
                section_title="3 QLoRA Finetuning",
                page_numbers=[3],
                content="QLoRA backpropagates gradients through a frozen 4-bit quantized pretrained language model into Low Rank Adapters using 4-bit NormalFloat (NF4).",
            ),
        ]
    )

    retriever = HybridGraphRetriever(
        vector_store=vector_store,
        citation_graph=citation_graph,
        reranker=CrossEncoderReranker(use_cross_encoder=False),
    )
    return LiteratureReviewAgent(retriever=retriever)


def test_agentic_query_decomposition_and_grounded_synthesis(tmp_path: Path):
    agent = build_mock_literature_agent(tmp_path)
    question = "Compare LoRA vs QLoRA for finetuning large language models"

    response = agent.run(question)

    assert len(response.sub_queries) >= 2
    assert len(response.citations) == 2
    assert response.is_grounded is True
    assert "2106.09685" in response.answer
    assert "2305.14314" in response.answer


def test_rag_evaluation_pipeline(tmp_path: Path):
    agent = build_mock_literature_agent(tmp_path)
    evaluator = RAGEvaluator()

    samples = [
        EvalSample(
            question="Compare LoRA vs QLoRA quantization and rank decomposition",
            expected_paper_ids=["2106.09685", "2305.14314"],
            expected_keywords=["4-bit", "NormalFloat", "rank"],
        )
    ]

    summary = evaluator.run_benchmark(agent=agent, samples=samples)
    assert summary["num_samples"] == 1
    assert summary["mean_context_precision"] == 1.0
    assert summary["mean_context_recall"] == 1.0
    assert summary["mean_citation_faithfulness"] == 1.0
    assert summary["mean_answer_relevance"] > 0.5


def test_llm_client_custom_url_and_gemini_resolution():
    # 1. Official Gemini endpoint
    gemini_client = LLMClient(
        api_key="test-key-123",
        model_name="gemini-2.5-flash",
        provider="gemini",
        base_url="",
    )
    assert not gemini_client.is_openai_compatible
    assert (
        gemini_client.resolve_endpoint_url()
        == "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=test-key-123"
    )

    # 2. Custom Gemini proxy URL
    gemini_proxy = LLMClient(
        api_key="proxy-key",
        model_name="gemini-2.5-flash",
        provider="gemini",
        base_url="https://my-gemini-proxy.example.com",
    )
    assert not gemini_proxy.is_openai_compatible
    assert (
        gemini_proxy.resolve_endpoint_url()
        == "https://my-gemini-proxy.example.com/v1beta/models/gemini-2.5-flash:generateContent?key=proxy-key"
    )

    # 3. Custom OpenAI-compatible URL (e.g. Ollama / vLLM / LiteLLM)
    custom_client = LLMClient(
        api_key="custom-token",
        model_name="qwen2.5:7b",
        provider="custom",
        base_url="http://localhost:11434/v1",
    )
    assert custom_client.is_openai_compatible
    assert custom_client.resolve_endpoint_url() == "http://localhost:11434/v1/chat/completions"
