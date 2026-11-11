from typing import List, Optional, Tuple

from src.config import settings
from src.indexing.citation_graph import CitationGraphStore
from src.indexing.vector_store import HybridVectorStore
from src.models.schemas import RetrievedPassage
from src.retrieval.reranker import CrossEncoderReranker


class HybridGraphRetriever:
    """
    Combines:
    1. Hybrid Retrieval (Dense Qdrant + Sparse BM25 via Reciprocal Rank Fusion)
    2. Neural Cross-Encoder Re-ranking (FastEmbed ONNX)
    3. Citation Graph Traversal (finding co-cited papers and shared references)
    """

    def __init__(
        self,
        vector_store: HybridVectorStore,
        citation_graph: CitationGraphStore,
        reranker: Optional[CrossEncoderReranker] = None,
        search_mode: str = "hybrid",
    ):
        self.vector_store = vector_store
        self.citation_graph = citation_graph
        self._reranker = reranker
        self.search_mode = search_mode

    @property
    def reranker(self) -> CrossEncoderReranker:
        if self._reranker is None:
            self._reranker = CrossEncoderReranker(use_cross_encoder=True)
        return self._reranker

    def retrieve(
        self,
        query: str,
        initial_top_k: int = settings.initial_top_k,
        rerank_top_k: int = settings.rerank_top_k,
        paper_id_filter: Optional[str] = None,
        mode: Optional[str] = None,
    ) -> Tuple[List[RetrievedPassage], List[str]]:
        """
        Retrieve and rerank top passages for a query, and expand via the citation graph.
        Returns: (reranked_passages, related_papers_from_graph)
        """
        active_mode = mode or self.search_mode
        candidates = self.vector_store.hybrid_search(
            query=query,
            top_k=initial_top_k,
            paper_id_filter=paper_id_filter,
            mode=active_mode,
        )
        top_passages = self.reranker.rerank(
            query=query,
            passages=candidates,
            top_k=rerank_top_k,
        )

        active_paper_ids = list({p.chunk.paper_id for p in top_passages})
        related_graph_papers = self.citation_graph.get_related_papers(active_paper_ids)

        return top_passages, related_graph_papers
