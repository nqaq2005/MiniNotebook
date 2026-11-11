import hashlib
import logging
import math
import re
import uuid
from typing import Dict, List, Optional, Protocol
from rank_bm25 import BM25Okapi

from src.config import settings
from src.models.schemas import RetrievedPassage, SectionChunk

logger = logging.getLogger(__name__)


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+(?:[-_][a-zA-Z0-9]+)*")


def tokenize_scientific_text(text: str) -> List[str]:
    """Tokenize academic text while preserving hyphenated terms like '4-bit', 'bge-m3', 'LoRA'."""
    return [tok.lower() for tok in TOKEN_PATTERN.findall(text)]


class EmbedderProtocol(Protocol):
    """Protocol for dense text embedding models."""

    @property
    def dimension(self) -> int: ...

    def embed_documents(self, texts: List[str]) -> List[List[float]]: ...

    def embed_query(self, text: str) -> List[float]: ...


class HashingEmbedder:
    """
    Lightweight, deterministic feature-hashing embedder for fast unit testing
    and offline fallback when neural weights are not yet cached.
    """

    def __init__(self, dimension: int = 384):
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    def _embed_single(self, text: str) -> List[float]:
        vec = [0.0] * self._dim
        tokens = tokenize_scientific_text(text)
        if not tokens:
            return vec
        for tok in tokens:
            digest = hashlib.md5(tok.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "little") % self._dim
            sign = 1.0 if (digest[4] % 2 == 0) else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_single(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed_single(text)


class FastEmbedder:
    """
    Production neural dense embedder powered by FastEmbed + ONNX Runtime
    (e.g., BAAI/bge-small-en-v1.5, BAAI/bge-base-en-v1.5).
    Caches ONNX weights in data/models_cache for fast offline reuse.
    """

    def __init__(self, model_name: str = settings.embedding_model):
        from fastembed import TextEmbedding

        self.model_name = model_name
        cache_dir = settings.models_cache_dir
        has_cached = any(cache_dir.glob("models--*"))
        try:
            self.model = TextEmbedding(
                model_name=model_name,
                cache_dir=str(cache_dir),
                local_files_only=has_cached,
            )
        except Exception:
            self.model = TextEmbedding(
                model_name=model_name,
                cache_dir=str(cache_dir),
                local_files_only=False,
            )
        sample_vec = next(self.model.embed(["dimension check"]))
        self._dim = len(sample_vec)

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        return [vec.tolist() for vec in self.model.embed(texts)]

    def embed_query(self, text: str) -> List[float]:
        vec = next(self.model.query_embed(text))
        return vec.tolist()


def get_default_embedder(in_memory: bool = False) -> EmbedderProtocol:
    """Return FastEmbedder for production storage, falling back to HashingEmbedder if in-memory/offline."""
    if in_memory:
        return HashingEmbedder()
    try:
        return FastEmbedder(model_name=settings.embedding_model)
    except Exception as exc:
        import warnings
        warnings.warn(
            f"[MiniNotebook Warning] Failed to initialize FastEmbedder ({exc}). "
            "Falling back to HashingEmbedder for offline/test mode. "
            "Embeddings will not be semantically meaningful until fastembed is installed and model downloaded.",
            RuntimeWarning,
            stacklevel=2,
        )
        return HashingEmbedder()


class HybridVectorStore:
    """
    Hybrid Retrieval Store combining:
    1. Dense Vector Search (Qdrant local or in-memory with BGE ONNX embeddings)
    2. Sparse Lexical Search (BM25Okapi)
    3. Reciprocal Rank Fusion (RRF) to merge dense + lexical rankings
    """

    def __init__(
        self,
        embedder: Optional[EmbedderProtocol] = None,
        collection_name: str = settings.qdrant_collection_name,
        in_memory: bool = False,
    ):
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        self.embedder: EmbedderProtocol = embedder or get_default_embedder(in_memory=in_memory)
        self.collection_name = collection_name

        if in_memory:
            self.client = QdrantClient(":memory:")
        else:
            self.client = None
            if settings.qdrant_url.strip():
                try:
                    c = QdrantClient(url=settings.qdrant_url.strip(), timeout=3.0)
                    c.collection_exists(self.collection_name)
                    self.client = c
                except Exception as e:
                    logger.warning(f"Cannot connect to Qdrant at {settings.qdrant_url} ({e}). Falling back to local storage.")
                    self.client = None

            if self.client is None:
                try:
                    self.client = QdrantClient(path=str(settings.vector_db_dir))
                except RuntimeError as exc:
                    import warnings
                    warnings.warn(
                        f"[MiniNotebook Warning] Local storage at '{settings.vector_db_dir}' is locked ({exc}). "
                        "Falling back to ephemeral in-memory Qdrant. Data will not persist across restarts.",
                        RuntimeWarning,
                        stacklevel=2,
                    )
                    self.client = QdrantClient(":memory:")

        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedder.dimension,
                    distance=Distance.COSINE,
                ),
            )

        self.chunks_by_id: Dict[str, SectionChunk] = {}
        self._bm25: Optional[BM25Okapi] = None
        self._bm25_chunk_ids: List[str] = []
        self._bm25_dirty: bool = False
        self._sync_bm25_from_qdrant()

    def _sync_bm25_from_qdrant(self) -> None:
        """Rebuild the in-memory BM25 index from stored Qdrant payloads on startup with pagination."""
        offset = None
        while True:
            points, next_offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for pt in points:
                payload = pt.payload or {}
                if "chunk_id" in payload:
                    chunk = SectionChunk(**payload)
                    self.chunks_by_id[chunk.chunk_id] = chunk
            if next_offset is None or not points:
                break
            offset = next_offset
        self._rebuild_bm25()

    def _rebuild_bm25(self) -> None:
        self._bm25_chunk_ids = list(self.chunks_by_id.keys())
        if not self._bm25_chunk_ids:
            self._bm25 = None
            self._bm25_dirty = False
            return
        corpus = [
            tokenize_scientific_text(
                f"{self.chunks_by_id[cid].paper_title} {self.chunks_by_id[cid].section_title} {self.chunks_by_id[cid].content}"
            )
            for cid in self._bm25_chunk_ids
        ]
        self._bm25 = BM25Okapi(corpus)
        self._bm25_dirty = False

    def _ensure_bm25(self) -> None:
        """Lazily rebuild BM25 only when dirty before search."""
        if self._bm25_dirty or (self.chunks_by_id and self._bm25 is None):
            self._rebuild_bm25()

    @staticmethod
    def _chunk_id_to_uuid(chunk_id: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))

    def index_chunks(self, chunks: List[SectionChunk]) -> int:
        """Index a list of SectionChunks into both Qdrant (dense) and BM25 (sparse)."""
        if not chunks:
            return 0

        from qdrant_client.models import PointStruct

        texts_to_embed = [
            f"{c.paper_title} | {c.section_title}\n{c.content}" for c in chunks
        ]
        vectors = self.embedder.embed_documents(texts_to_embed)

        points = [
            PointStruct(
                id=self._chunk_id_to_uuid(chunk.chunk_id),
                vector=vec,
                payload=chunk.model_dump(),
            )
            for chunk, vec in zip(chunks, vectors)
        ]
        self.client.upsert(collection_name=self.collection_name, points=points)

        for chunk in chunks:
            self.chunks_by_id[chunk.chunk_id] = chunk

        self._bm25_dirty = True
        return len(chunks)

    def reindex_all(self) -> int:
        """Re-compute dense embeddings for all currently stored chunks using the active embedder."""
        all_chunks = list(self.chunks_by_id.values())
        if not all_chunks:
            return 0
        return self.index_chunks(all_chunks)

    def delete_paper_chunks(self, paper_id: str) -> int:
        """Delete all chunks belonging to a specific paper_id from Qdrant and BM25."""
        target_cids = [
            cid for cid, chunk in self.chunks_by_id.items() if chunk.paper_id == paper_id
        ]
        if not target_cids:
            return 0

        point_uuids = [self._chunk_id_to_uuid(cid) for cid in target_cids]
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=point_uuids,
        )
        for cid in target_cids:
            self.chunks_by_id.pop(cid, None)
        self._bm25_dirty = True
        return len(target_cids)

    def hybrid_search(
        self,
        query: str,
        top_k: int = settings.initial_top_k,
        paper_id_filter: Optional[str] = None,
        rrf_k: int = 60,
        mode: str = "hybrid",
    ) -> List[RetrievedPassage]:
        """
        Execute retrieval in one of three modes:
        - 'hybrid': Dense Vector Search (Qdrant) + Sparse Lexical Search (BM25) fused via RRF
        - 'dense': Dense Vector Search (Qdrant) only
        - 'sparse': Sparse Lexical Search (BM25) only
        """
        if not self.chunks_by_id:
            return []

        self._ensure_bm25()

        from qdrant_client.models import FieldCondition, Filter, MatchValue

        query_filter = None
        if paper_id_filter:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="paper_id",
                        match=MatchValue(value=paper_id_filter),
                    )
                ]
            )

        # 1. Dense Search via Qdrant
        dense_ranks: Dict[str, int] = {}
        dense_scores: Dict[str, float] = {}
        if mode in ("hybrid", "dense"):
            query_vec = self.embedder.embed_query(query)
            dense_res = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vec,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            ).points

            for rank_idx, pt in enumerate(dense_res):
                cid = (pt.payload or {}).get("chunk_id")
                if cid:
                    dense_ranks[cid] = rank_idx + 1
                    dense_scores[cid] = float(pt.score or 0.0)

        # 2. Sparse Lexical Search via BM25
        sparse_ranks: Dict[str, int] = {}
        sparse_scores: Dict[str, float] = {}
        if mode in ("hybrid", "sparse") and self._bm25 is not None:
            query_tokens = tokenize_scientific_text(query)
            raw_bm25_scores = self._bm25.get_scores(query_tokens)
            scored_pairs = [
                (cid, float(score))
                for cid, score in zip(self._bm25_chunk_ids, raw_bm25_scores)
                if (paper_id_filter is None or self.chunks_by_id[cid].paper_id == paper_id_filter)
            ]
            scored_pairs.sort(key=lambda x: x[1], reverse=True)
            for rank_idx, (cid, score) in enumerate(scored_pairs[:top_k]):
                sparse_ranks[cid] = rank_idx + 1
                sparse_scores[cid] = score

        # 3. Rank Fusion / Scoring
        candidate_ids = set(dense_ranks.keys()) | set(sparse_ranks.keys())
        fused_results: List[tuple[float, RetrievedPassage]] = []

        for cid in candidate_ids:
            chunk = self.chunks_by_id.get(cid)
            if not chunk:
                continue
            rrf_score = 0.0
            if cid in dense_ranks:
                rrf_score += 1.0 / (rrf_k + dense_ranks[cid])
            if cid in sparse_ranks:
                rrf_score += 1.0 / (rrf_k + sparse_ranks[cid])

            passage = RetrievedPassage(
                chunk=chunk,
                dense_score=dense_scores.get(cid, 0.0),
                sparse_score=sparse_scores.get(cid, 0.0),
                rerank_score=rrf_score,
            )
            fused_results.append((rrf_score, passage))

        fused_results.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in fused_results[:top_k]]
