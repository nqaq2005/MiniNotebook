from pathlib import Path
from src.indexing.citation_graph import CitationGraphStore
from src.indexing.vector_store import HashingEmbedder, HybridVectorStore
from src.models.schemas import PaperMetadata, SectionChunk
from src.retrieval.hybrid_retriever import HybridGraphRetriever
from src.retrieval.reranker import CrossEncoderReranker


def test_citation_graph_co_citation_and_persistence(tmp_path: Path):
    graph_file = tmp_path / "graph.json"
    store = CitationGraphStore(graph_path=graph_file)

    paper_lora = PaperMetadata(
        paper_id="2106.09685",
        title="LoRA: Low-Rank Adaptation of Large Language Models",
        authors=["Edward J. Hu"],
        references=["W_TRANSFORMER", "W_GPT3"],
        citation_count=5000,
    )
    paper_qlora = PaperMetadata(
        paper_id="2305.14314",
        title="QLoRA: Efficient Finetuning of Quantized LLMs",
        authors=["Tim Dettmers"],
        references=["2106.09685", "W_TRANSFORMER"],
        citation_count=2500,
    )

    store.add_paper(paper_lora)
    store.add_paper(paper_qlora)
    store.save()

    reloaded = CitationGraphStore(graph_path=graph_file)
    stats = reloaded.get_stats()
    assert stats["ingested_papers"] == 2
    assert stats["total_citation_edges"] == 4

    related = reloaded.get_related_papers(["2106.09685"])
    assert any("2305.14314" in item for item in related)


def test_hybrid_vector_store_and_graph_retriever(tmp_path: Path):
    vector_store = HybridVectorStore(
        embedder=HashingEmbedder(dimension=128),
        collection_name="test_papers",
        in_memory=True,
    )
    citation_graph = CitationGraphStore(graph_path=tmp_path / "graph.json")

    citation_graph.add_paper(
        PaperMetadata(
            paper_id="2106.09685",
            title="LoRA: Low-Rank Adaptation",
            references=["W_SHARED"],
        )
    )
    citation_graph.add_paper(
        PaperMetadata(
            paper_id="2305.14314",
            title="QLoRA: Quantized LLMs",
            references=["2106.09685", "W_SHARED"],
        )
    )

    chunks = [
        SectionChunk(
            chunk_id="2106.09685_sec1_0",
            paper_id="2106.09685",
            paper_title="LoRA: Low-Rank Adaptation",
            section_title="2 Method",
            page_numbers=[3],
            content="LoRA freezes pretrained model weights and injects trainable rank decomposition matrices.",
        ),
        SectionChunk(
            chunk_id="2305.14314_sec2_0",
            paper_id="2305.14314",
            paper_title="QLoRA: Quantized LLMs",
            section_title="3 4-bit NormalFloat",
            page_numbers=[4, 5],
            content="QLoRA uses 4-bit NormalFloat (NF4) quantization and double quantization to reduce memory.",
        ),
    ]
    count = vector_store.index_chunks(chunks)
    assert count == 2

    retriever = HybridGraphRetriever(
        vector_store=vector_store,
        citation_graph=citation_graph,
        reranker=CrossEncoderReranker(use_cross_encoder=False),
    )

    passages, related_papers = retriever.retrieve(
        query="How does 4-bit NormalFloat NF4 quantization work in QLoRA?",
        initial_top_k=5,
        rerank_top_k=2,
    )

    assert len(passages) == 2
    assert passages[0].chunk.paper_id == "2305.14314"
    assert "[2305.14314: 3 4-bit NormalFloat, p.4,5]" == passages[0].citation_tag
    assert len(related_papers) > 0
