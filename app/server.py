import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.agent.nodes import LLMClient
from src.agent.workflow import LiteratureReviewAgent, passage_to_dict
from src.config import settings
from src.indexing.citation_graph import CitationGraphStore
from src.indexing.vector_store import HybridVectorStore
from src.ingestion.pipeline import IngestionPipeline
from src.retrieval.hybrid_retriever import HybridGraphRetriever
from src.retrieval.reranker import CrossEncoderReranker


app = FastAPI(
    title="MiniNotebook API",
    description="NotebookLM-Style AI Research Assistant & Markdown Workspace",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

vector_store = HybridVectorStore()
citation_graph = CitationGraphStore()
pipeline = IngestionPipeline(vector_store=vector_store, citation_graph=citation_graph)

# Load the ONNX Cross-Encoder ONCE and share it across requests
# (previously it was re-loaded from disk on every /api/ask call).
shared_reranker = CrossEncoderReranker()
_retrievers: Dict[str, HybridGraphRetriever] = {}


def get_retriever(search_mode: str) -> HybridGraphRetriever:
    mode = search_mode if search_mode in ("hybrid", "dense", "sparse") else "hybrid"
    if mode not in _retrievers:
        _retrievers[mode] = HybridGraphRetriever(
            vector_store=vector_store,
            citation_graph=citation_graph,
            reranker=shared_reranker,
            search_mode=mode,
        )
    return _retrievers[mode]


@app.get("/healthz")
def healthz():
    """Liveness probe for Docker container and orchestrators."""
    return {"status": "ok"}

HTML_PATH = Path(__file__).resolve().parent / "index.html"
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class IngestRequest(BaseModel):
    query: str
    max_papers: int = 2


class AskRequest(BaseModel):
    question: str
    search_mode: str = "hybrid"
    paper_id_filter: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_base_url: Optional[str] = None
    api_key: Optional[str] = None
    reasoning_effort: Optional[str] = None
    language: Optional[str] = "vi"


def _truncate_title(title: str, max_len: int = 38) -> str:
    cleaned = " ".join(title.split())
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 1].rstrip() + "…"


from collections import defaultdict


def _build_papers_list() -> List[dict]:
    items = []
    chunks_by_paper = defaultdict(list)
    for c in vector_store.chunks_by_id.values():
        chunks_by_paper[c.paper_id].append(c)

    for node_id, attr in citation_graph.graph.nodes(data=True):
        if attr.get("ingested", False):
            chunks = chunks_by_paper.get(node_id, [])
            sections = list(dict.fromkeys(c.section_title for c in chunks))
            abstract_chunk = next((c.content for c in chunks if c.section_title.lower() == "abstract"), "")
            items.append(
                {
                    "paper_id": node_id,
                    "title": attr.get("title", node_id),
                    "authors": attr.get("authors", []),
                    "published_date": attr.get("published_date") or "N/A",
                    "citation_count": attr.get("citation_count", 0),
                    "out_refs": citation_graph.graph.out_degree(node_id),
                    "chunk_count": len(chunks),
                    "sections": sections,
                    "abstract": abstract_chunk[:550] + ("…" if len(abstract_chunk) > 550 else ""),
                }
            )
    return items


def _build_suggestions(papers: List[dict]) -> List[dict]:
    if not papers:
        return []
    first = papers[0]["title"]
    short1 = _truncate_title(first, 36)
    suggestions = [
        {
            "label": f"Main contributions of {short1}",
            "question": f"What are the main methodology, architectural innovations, and key experimental findings of '{first}'?",
        }
    ]
    if len(papers) >= 2:
        second = papers[1]["title"]
        short2 = _truncate_title(second, 32)
        suggestions.append(
            {
                "label": f"Compare: { _truncate_title(first, 20) } vs { _truncate_title(second, 20) }",
                "question": f"Compare the methodology, key differences, and experimental results between '{first}' and '{second}'.",
            }
        )
    else:
        suggestions.append(
            {
                "label": "Experimental setup & benchmarks",
                "question": f"What datasets, evaluation metrics, and ablation studies are reported in '{first}'?",
            }
        )
    suggestions.append(
        {
            "label": "Synthesis of limitations & future work",
            "question": "What are the main limitations, bottlenecks, or future work directions discussed across the indexed papers?",
        }
    )
    return suggestions


@app.get("/", response_class=HTMLResponse)
def serve_ui():
    if not HTML_PATH.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(HTML_PATH)


_shared_llm_client: Optional[LLMClient] = None


def get_shared_llm_client() -> LLMClient:
    global _shared_llm_client
    if _shared_llm_client is None:
        _shared_llm_client = LLMClient()
    return _shared_llm_client


@app.get("/api/stats")
def get_stats():
    g_stats = citation_graph.get_stats()
    papers = _build_papers_list()
    llm_check = get_shared_llm_client()
    return {
        "metrics": {
            "ingested_papers": len(papers),
            "indexed_chunks": len(vector_store.chunks_by_id),
            "total_nodes": g_stats.get("total_nodes", len(papers)),
            "total_citation_edges": g_stats.get("total_citation_edges", 0),
        },
        "config": {
            "llm_provider": settings.llm_provider,
            "llm_model": settings.llm_model,
            "llm_base_url": settings.llm_base_url,
            "llm_reasoning_effort": settings.llm_reasoning_effort,
            "llm_language": getattr(settings, "llm_language", "vi"),
            "llm_configured": llm_check.is_configured,
            "embedder": type(vector_store.embedder).__name__,
            "embedding_model": settings.embedding_model,
            "reranker_model": settings.reranker_model,
        },
        "papers": papers,
        "suggestions": _build_suggestions(papers),
        "graph": {"total_nodes": g_stats["total_nodes"], "total_edges": g_stats["total_citation_edges"]},
    }


@app.post("/api/ingest")
def ingest_papers(req: IngestRequest):
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Truy vấn tìm kiếm không được để trống.")
    try:
        stats = pipeline.ingest_topic(query=query, max_papers=max(1, min(req.max_papers, 10)))
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi tải hoặc lập chỉ mục từ ArXiv: {str(e)}",
        )


MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


@app.post("/api/upload")
def upload_pdf(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a valid .pdf file.")

    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File size exceeds the maximum limit of 50MB.")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Invalid PDF file format (missing %PDF- header).")

    safe_name = Path(file.filename).name
    save_path = settings.raw_pdf_dir / safe_name
    save_path.write_bytes(content)

    info = pipeline.ingest_local_pdf(
        pdf_path=save_path,
        title=title.strip() if title and title.strip() else None,
    )
    return info


@app.delete("/api/papers/{paper_id}")
def delete_paper(paper_id: str):
    removed_chunks = pipeline.delete_paper(paper_id)
    return {"paper_id": paper_id, "removed_chunks": removed_chunks}


def _build_agent(req: "AskRequest") -> LiteratureReviewAgent:
    llm_client = LLMClient(
        api_key=req.api_key if req.api_key else None,
        model_name=req.llm_model if req.llm_model else None,
        provider=req.llm_provider if req.llm_provider else None,
        base_url=req.llm_base_url if req.llm_base_url is not None else None,
        reasoning_effort=req.reasoning_effort if req.reasoning_effort else None,
    )
    return LiteratureReviewAgent(retriever=get_retriever(req.search_mode), llm_client=llm_client)


@app.post("/api/ask")
def ask_question(req: AskRequest):
    """Non-streaming endpoint (kept for scripts / Swagger). The web UI uses /api/ask/stream."""
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    lang = req.language or getattr(settings, "llm_language", "vi")
    resp = _build_agent(req).run(
        question,
        language=lang,
        paper_id_filter=req.paper_id_filter,
    )
    return {
        "question": resp.question,
        "sub_queries": resp.sub_queries,
        "answer": resp.answer,
        "is_grounded": resp.is_grounded,
        "related_papers_from_graph": resp.related_papers_from_graph,
        "citations": [passage_to_dict(p) for p in resp.citations],
    }


@app.post("/api/ask/stream")
def ask_question_stream(req: AskRequest):
    """
    Streams NDJSON events (one JSON object per line) from the first model token:
      status -> sources -> thinking* / token* (or fallback) -> done
    If the browser disconnects, the generator is closed and the upstream LLM request is cancelled.
    """
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    agent = _build_agent(req)
    lang = req.language or getattr(settings, "llm_language", "vi")

    def event_lines():
        try:
            for event in agent.run_stream(
                question,
                language=lang,
                paper_id_filter=req.paper_id_filter,
            ):
                if event.get("type") == "done":
                    t = event.get("timings", {})
                    print(
                        f"[MiniNotebook] retrieval={t.get('retrieval_ms')}ms "
                        f"ttft={t.get('ttft_ms')}ms llm={t.get('llm_ms')}ms total={t.get('total_ms')}ms"
                    )
                yield json.dumps(event, ensure_ascii=False) + "\n"
        except Exception as exc:  # never break the stream with a raw traceback
            yield json.dumps({"type": "error", "message": f"{type(exc).__name__}: {exc}"}) + "\n"

    return StreamingResponse(
        event_lines(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
