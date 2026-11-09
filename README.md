# 🎓 ScholarRAG — AI Literature Review & Citation Graph Assistant

An **Agentic & Section-Aware Hybrid GraphRAG** system built for analyzing scientific papers, comparing methodologies across publications, and exploring citation networks with strict section- & page-level grounding.

---

## ✨ Key Architectural Highlights

1. **Layout- & Section-Aware PDF Ingestion (`PyMuPDF4LLM` + `RapidOCR`)**:
   - Converts multi-column academic PDFs (including figures, diagrams, and tables) into structured Markdown.
   - Splits papers by logical academic sections (`Abstract`, `Introduction`, `Methodology`, `Experiments`, `Conclusion`) via [`SectionAwareChunker`](src/ingestion/chunker.py) while automatically stripping out noisy `References`/`Bibliography` text.
   - Fetches papers directly from **ArXiv** (with automatic fallback to **OpenAlex** on HTTP 429 rate-limits) or via **Local PDF Upload**.

2. **Hybrid Search + ONNX Neural Cross-Encoder Reranking**:
   - **Dense Vector Search**: Powered by `Qdrant` and ONNX `BAAI/bge-small-en-v1.5` (`FastEmbedder`).
   - **Sparse Lexical Search**: Powered by `BM25Okapi` with custom scientific tokenization preserving technical terms (`4-bit`, `NF4`, `bge-m3`).
   - **Reciprocal Rank Fusion (RRF) & Cross-Encoder**: Merges candidate lists and re-scores top passages using `Xenova/ms-marco-MiniLM-L-6-v2` via ONNX Runtime.

3. **Citation Graph Exploration (`NetworkX` + `Graphviz`)**:
   - Builds a directed citation graph enriched with OpenAlex reference data.
   - Identifies **co-cited foundational works** and **bibliographically coupled papers** (`get_related_papers`) and renders an interactive network diagram in the UI.

4. **4-Stage Agentic RAG Workflow**:
   - `decompose_query`: Splits comparative questions into targeted sub-queries.
   - `retrieve_evidence`: Executes multi-query hybrid + graph retrieval.
   - `synthesize_answer`: Generates grounded literature reviews (supporting both **Google Gemini API** and any **Custom OpenAI-Compatible URL** such as Ollama, vLLM, or LiteLLM).
   - `verify_grounding`: Citation & Hallucination Guard verifying that every `[paper_id: Section, p.X]` tag matches retrieved sources.

5. **Quantitative Evaluation & Ablation Benchmark**:
   - Automated benchmark comparing **Dense-Only** vs. **Sparse BM25-Only** vs. **Hybrid + Cross-Encoder** across *Context Precision*, *Context Recall*, *Citation Faithfulness*, and *Answer Relevance*.

---

## 🚀 Quickstart (Fish Shell)

```fish
# 1. Kích hoạt môi trường ảo trên Fish shell
source .venv/bin/activate.fish

# 2. Cài đặt dependencies
pip install -r requirements.txt

# 3. Tạo file cấu hình biến môi trường
cp .env.example .env

# 4. Khởi chạy Web App ScholarRAG với FastAPI (Siêu nhẹ & Nhanh)
uvicorn app.server:app --reload --port 8000
# Mở trình duyệt tại: http://localhost:8000 (hoặc Swagger API tại http://localhost:8000/docs)
```

### 💻 Sử dụng qua CLI (`fish` shell)

```fish
# Kiểm tra thống kê thư viện & đồ thị trích dẫn
python cli.py stats

# Tải và phân tích bài báo từ ArXiv
python cli.py ingest -q "3D Gaussian Splatting radiance fields" -n 2

# Đặt câu hỏi nghiên cứu / so sánh
python cli.py ask -q "How does 3D Gaussian Splatting achieve real-time rendering?"

# Chạy thực nghiệm đối sánh (Ablation Study: Dense vs BM25 vs Hybrid)
python cli.py eval
```
