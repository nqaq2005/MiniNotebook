import math
from typing import List

from src.config import settings
from src.indexing.vector_store import tokenize_scientific_text
from src.models.schemas import RetrievedPassage


class CrossEncoderReranker:
    """
    Re-ranks retrieved candidate passages using an ONNX Cross-Encoder model via FastEmbed
    (e.g., Xenova/ms-marco-MiniLM-L-6-v2 or BAAI/bge-reranker-base), with graceful fallback
    to calibrated lexical + RRF re-scoring when running in unit-test or offline mode.
    """

    def __init__(
        self,
        model_name: str = settings.reranker_model,
        use_cross_encoder: bool = True,
    ):
        self.model_name = model_name
        self.use_cross_encoder = use_cross_encoder
        self._cross_encoder = None

        if self.use_cross_encoder:
            try:
                from fastembed.rerank.cross_encoder import TextCrossEncoder

                cache_dir = settings.models_cache_dir
                # Default to fast 85MB ONNX CrossEncoder if legacy uncached bge-reranker-base is set in .env
                target_model = self.model_name
                if (
                    target_model == "BAAI/bge-reranker-base"
                    and not any((cache_dir / "models--BAAI--bge-reranker-base" / "snapshots").glob("*/*.onnx"))
                ):
                    target_model = "Xenova/ms-marco-MiniLM-L-6-v2"
                    self.model_name = target_model

                slug = f"models--{target_model.replace('/', '--')}"
                is_cached = any((cache_dir / slug / "snapshots").glob("*/*.onnx"))
                self._cross_encoder = TextCrossEncoder(
                    model_name=target_model,
                    cache_dir=str(cache_dir),
                    local_files_only=is_cached,
                )
            except Exception:
                self._cross_encoder = None

    @staticmethod
    def _sigmoid(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-max(min(x, 20.0), -20.0)))

    def rerank(
        self,
        query: str,
        passages: List[RetrievedPassage],
        top_k: int = settings.rerank_top_k,
    ) -> List[RetrievedPassage]:
        """Re-score and sort passages by neural cross-encoder + hybrid signals."""
        if not passages:
            return []

        if self._cross_encoder is not None:
            docs = [
                f"{p.chunk.paper_title} | {p.chunk.section_title}\n{p.chunk.content}"
                for p in passages
            ]
            raw_scores = list(self._cross_encoder.rerank(query=query, documents=docs))
            max_sparse = max((p.sparse_score for p in passages), default=0.0) or 1.0

            for passage, ce_logit in zip(passages, raw_scores):
                ce_prob = self._sigmoid(float(ce_logit))
                norm_sparse = passage.sparse_score / max_sparse if passage.sparse_score > 0 else 0.0
                # Combine Cross-Encoder probability with RRF + normalized lexical signal
                passage.rerank_score = 0.70 * ce_prob + 0.20 * norm_sparse + 0.10 * float(passage.rerank_score)
        else:
            q_tokens = tokenize_scientific_text(query)
            q_set = set(q_tokens)
            q_bigrams = {f"{q_tokens[i]}_{q_tokens[i+1]}" for i in range(len(q_tokens) - 1)}

            max_sparse = max((p.sparse_score for p in passages), default=0.0) or 1.0
            max_dense = max((p.dense_score for p in passages), default=0.0) or 1.0

            for passage in passages:
                title_tokens = set(tokenize_scientific_text(passage.chunk.paper_title))
                sec_tokens = set(tokenize_scientific_text(passage.chunk.section_title))
                body_tokens = tokenize_scientific_text(passage.chunk.content)
                d_set = title_tokens | sec_tokens | set(body_tokens)
                d_bigrams = {
                    f"{body_tokens[i]}_{body_tokens[i+1]}" for i in range(len(body_tokens) - 1)
                }

                token_overlap = len(q_set & d_set) / max(len(q_set), 1)
                title_overlap = len(q_set & title_tokens) / max(len(q_set), 1)
                bigram_overlap = len(q_bigrams & d_bigrams) / max(len(q_bigrams), 1) if q_bigrams else 0.0

                norm_sparse = passage.sparse_score / max_sparse if passage.sparse_score > 0 else 0.0
                norm_dense = passage.dense_score / max_dense if passage.dense_score > 0 else 0.0

                passage.rerank_score = (
                    float(passage.rerank_score)
                    + 0.45 * token_overlap
                    + 0.35 * title_overlap
                    + 0.25 * bigram_overlap
                    + 0.30 * norm_sparse
                    + 0.15 * norm_dense
                )

        ranked = sorted(passages, key=lambda p: p.rerank_score, reverse=True)
        return ranked[:top_k]
