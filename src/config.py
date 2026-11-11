import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Ensure localhost and 127.0.0.1 are bypassed by system proxies (prevents 403 on local Qdrant/Ollama)
for _var in ("NO_PROXY", "no_proxy"):
    _cur = os.environ.get(_var, "")
    if _cur:
        if "localhost" not in _cur:
            os.environ[_var] = f"{_cur},localhost,127.0.0.1"
    else:
        os.environ[_var] = "localhost,127.0.0.1"


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Centralized configuration for ScholarRAG (AI Literature Review & Citation Graph Assistant)."""

    # API Keys
    gemini_api_key: str = ""
    openai_api_key: str = ""
    custom_api_key: str = ""
    cohere_api_key: str = ""

    # Model & Custom Endpoint Settings
    # llm_provider: "gemini" or "custom" (OpenAI-compatible /v1/chat/completions, Ollama, vLLM, OpenRouter, Proxy)
    llm_provider: str = "gemini"
    llm_model: str = "gemini-2.5-flash"
    llm_base_url: str = ""
    llm_timeout_seconds: float = 300.0
    # reasoning_effort for thinking models: "low", "medium", "high", or "off"
    llm_reasoning_effort: str = "medium"
    # Response language: "vi" (Tiếng Việt) or "en" (English)
    llm_language: str = "vi"
    # 0 = do not send max_tokens (let the server decide)
    llm_max_tokens: int = 0
    # Prompt budget: fewer / shorter passages => faster prefill & time-to-first-token
    llm_max_context_passages: int = 6
    llm_context_chars_per_passage: int = 1500
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    reranker_model: str = "Xenova/ms-marco-MiniLM-L-6-v2"

    # Storage Paths
    raw_pdf_dir: Path = BASE_DIR / "data" / "raw_pdfs"
    parsed_md_dir: Path = BASE_DIR / "data" / "parsed_md"
    vector_db_dir: Path = BASE_DIR / "data" / "vector_db"
    models_cache_dir: Path = BASE_DIR / "data" / "models_cache"
    citation_graph_path: Path = BASE_DIR / "data" / "citation_graph" / "graph.json"
    qdrant_url: str = ""
    qdrant_collection_name: str = "research_papers"

    # Retrieval Parameters
    chunk_max_chars: int = 1800
    chunk_overlap_chars: int = 200
    initial_top_k: int = 20
    rerank_top_k: int = 5

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def ensure_dirs(self) -> None:
        """Ensure all local data directories exist."""
        self.raw_pdf_dir.mkdir(parents=True, exist_ok=True)
        self.parsed_md_dir.mkdir(parents=True, exist_ok=True)
        self.vector_db_dir.mkdir(parents=True, exist_ok=True)
        self.models_cache_dir.mkdir(parents=True, exist_ok=True)
        self.citation_graph_path.parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
