import argparse
import json
from typing import Optional

from src.agent.nodes import LLMClient
from src.agent.workflow import LiteratureReviewAgent
from src.evaluation.eval_pipeline import RAGEvaluator, build_dynamic_benchmark
from src.indexing.citation_graph import CitationGraphStore
from src.indexing.vector_store import HybridVectorStore
from src.ingestion.pipeline import IngestionPipeline
from src.retrieval.hybrid_retriever import HybridGraphRetriever


def build_components(
    search_mode: str = "hybrid",
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    model_name: Optional[str] = None,
):
    vector_store = HybridVectorStore()
    citation_graph = CitationGraphStore()
    retriever = HybridGraphRetriever(
        vector_store=vector_store,
        citation_graph=citation_graph,
        search_mode=search_mode,
    )
    pipeline = IngestionPipeline(
        vector_store=vector_store,
        citation_graph=citation_graph,
    )
    llm_client = LLMClient(
        provider=provider,
        base_url=base_url,
        model_name=model_name,
    )
    agent = LiteratureReviewAgent(retriever=retriever, llm_client=llm_client)
    return vector_store, citation_graph, pipeline, agent


def main():
    parser = argparse.ArgumentParser(
        description="ScholarRAG CLI — AI Literature Review & Citation Graph Assistant"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Search ArXiv, download, parse, and index papers")
    ingest_parser.add_argument("--query", "-q", required=True, help="ArXiv search query or ID")
    ingest_parser.add_argument("--max-papers", "-n", type=int, default=2, help="Number of papers to ingest")

    subparsers.add_parser(
        "reindex",
        help="Re-embed all existing chunks in Qdrant with the active neural BGE Embedding model",
    )

    ask_parser = subparsers.add_parser("ask", help="Ask a literature review question")
    ask_parser.add_argument("--question", "-q", required=True, help="Research question to ask")
    ask_parser.add_argument(
        "--mode",
        choices=["hybrid", "dense", "sparse"],
        default="hybrid",
        help="Retrieval mode (default: hybrid)",
    )
    ask_parser.add_argument(
        "--provider",
        choices=["gemini", "custom"],
        default=None,
        help="LLM provider: 'gemini' or 'custom' (OpenAI-compatible endpoint)",
    )
    ask_parser.add_argument(
        "--base-url",
        default=None,
        help="Custom LLM base URL (e.g. http://localhost:11434/v1 or custom proxy URL)",
    )
    ask_parser.add_argument(
        "--model",
        default=None,
        help="Override LLM model name (e.g. gemini-2.5-flash, qwen2.5:7b)",
    )

    subparsers.add_parser("stats", help="Show Vector DB and Citation Graph statistics")
    subparsers.add_parser("eval", help="Run RAG evaluation & ablation benchmark (Dense vs BM25 vs Hybrid)")

    args = parser.parse_args()
    mode = getattr(args, "mode", "hybrid")
    provider = getattr(args, "provider", None)
    base_url = getattr(args, "base_url", None)
    model_name = getattr(args, "model", None)

    vector_store, citation_graph, pipeline, agent = build_components(
        search_mode=mode,
        provider=provider,
        base_url=base_url,
        model_name=model_name,
    )

    if args.command == "ingest":
        print(f"[*] Ingesting up to {args.max_papers} papers for query: '{args.query}'...")
        res = pipeline.ingest_topic(query=args.query, max_papers=args.max_papers)
        print(json.dumps(res, indent=2))

    elif args.command == "reindex":
        embedder_name = type(vector_store.embedder).__name__
        print(f"[*] Re-embedding all stored chunks using {embedder_name} ({getattr(vector_store.embedder, 'model_name', 'default')})...")
        count = vector_store.reindex_all()
        print(f"[+] Successfully re-embedded {count} chunks!")

    elif args.command == "ask":
        response = agent.run(args.question)
        print("\n=== DECOMPOSED SUB-QUERIES ===")
        for sq in response.sub_queries:
            print(f" - {sq}")
        print("\n=== SYNTHESIZED LITERATURE REVIEW ===")
        print(response.answer)
        print(f"\nGrounded Check: {response.is_grounded} | Citations used: {len(response.citations)}")

    elif args.command == "stats":
        stats = citation_graph.get_stats()
        stats["indexed_chunks"] = len(vector_store.chunks_by_id)
        stats["embedder"] = type(vector_store.embedder).__name__
        stats["reranker_active"] = agent.nodes.retriever.reranker._cross_encoder is not None
        print(json.dumps(stats, indent=2))

    elif args.command == "eval":
        evaluator = RAGEvaluator()
        dynamic_samples = build_dynamic_benchmark(vector_store)
        print(f"[*] Running Dynamic Ablation Study across {len(dynamic_samples)} questions from your ingested papers...")
        ablation = evaluator.run_ablation_study(
            vector_store=vector_store,
            citation_graph=citation_graph,
            samples=dynamic_samples,
        )
        print("\n=== ABLATION BENCHMARK SUMMARY ===")
        header = f"{'Mode':<10} | {'Ctx Precision':<14} | {'Ctx Recall':<12} | {'Faithfulness':<14} | {'Ans Relevance':<14}"
        print(header)
        print("-" * len(header))
        for m_name, metrics in ablation.items():
            print(
                f"{m_name:<10} | "
                f"{metrics['mean_context_precision']:<14.3f} | "
                f"{metrics['mean_context_recall']:<12.3f} | "
                f"{metrics['mean_citation_faithfulness']:<14.3f} | "
                f"{metrics['mean_answer_relevance']:<14.3f}"
            )


if __name__ == "__main__":
    main()
