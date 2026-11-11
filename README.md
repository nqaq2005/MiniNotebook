# 🎓 ScholarRAG — Trợ lý Nghiên cứu Khoa học & Workspace Markdown

**ScholarRAG** (tên giao diện: **MiniNotebook**) là hệ thống **Agentic & Section-Aware Hybrid GraphRAG** hiện đại được thiết kế phục vụ việc nghiên cứu, đọc hiểu, đối chiếu và tổng hợp tài liệu khoa học theo phong cách **NotebookLM**, kết hợp không gian soạn thảo ghi chú **Markdown** lấy cảm hứng từ **Obsidian**.

---

## ✨ Điểm nổi bật & Tính năng cốt lõi

### 1. 📝 Workspace Markdown Tích hợp (Obsidian-Inspired)
- **Soạn thảo linh hoạt song song với Chat**: Ghi chú ý tưởng, tóm tắt tài liệu ngay cạnh khung hỏi đáp.
- **2 Chế độ hiển thị thông minh**:
  - **Chia đôi màn hình (Split mode)**: Đặt song song với khung chat để vừa hỏi đáp vừa ghi chép.
  - **Phủ toàn bộ (Overlay mode)**: Mở rộng phủ trọn khu vực chat (vẫn giữ nguyên thanh nguồn bên trái) với hiệu ứng chuyển cảnh FLIP mượt mà.
- **3 Chế độ xem**: Chỉ soạn thảo (Editor only), Chia đôi xem trước (Split view), Xem trước hoàn chỉnh (Preview document).
- **Hành động 1-Click "Chèn vào Markdown"**: Nút tiện ích dưới mỗi câu trả lời AI giúp đưa nội dung tổng hợp và trích dẫn chuẩn xác thẳng vào bản ghi chú.
- **Tiện ích đầy đủ**: Phím tắt định dạng (`Ctrl+B`, `Ctrl+I`, `Tab`), mẫu bảng biểu, đếm từ/ký tự/dòng theo thời gian thực, tải file `.md`, sao chép nhanh và tự động lưu `localStorage`.

### 2. ⚡ Đa dạng Nhà cung cấp LLM (Multi-Provider Support)
Hệ thống hỗ trợ toàn diện các nền tảng LLM hàng đầu với khả năng streaming token ngay từ mili-giây đầu tiên:
- **Google Gemini**: Gọi native REST API (`gemini-2.5-flash`, `gemini-1.5-pro`, v.v.), hỗ trợ cấu hình ngân sách suy luận (*thinking budget*).
- **OpenAI**: Chuẩn `/v1/chat/completions` (`gpt-4o`, `gpt-4o-mini`, `o1`, `o3-mini`) kèm tham số `reasoning_effort`.
- **DeepSeek**: Hỗ trợ `deepseek-chat` (V3) và `deepseek-reasoner` (R1) — tự động bắt trường `reasoning_content` để hiển thị hộp suy luận riêng.
- **Groq**: Streaming siêu tốc với `llama-3.3-70b-versatile`, `deepseek-r1-distill-llama-70b`.
- **OpenRouter**: Truy cập hàng trăm mô hình mã nguồn mở và thương mại qua một API key.
- **Ollama / vLLM**: Chạy offline 100% trên máy cục bộ (`localhost`), không bắt buộc API key, có bộ định tuyến `_ThinkTagRouter` tự động bóc tách thẻ `<think>...</think>`.
- **Custom Endpoint**: Tùy biến mọi Base URL (LM Studio, LocalAI, Cloudflare Tunnel, LiteLLM).
- **Extractive Mode (Fallback dự phòng)**: Khi không có API key hoặc mất mạng, hệ thống tự động trích xuất các đoạn trích điểm cao nhất từ cơ sở dữ liệu để tổng hợp câu trả lời mà không bị lỗi.

### 3. 🔬 Xử lý Tài liệu Chuyên sâu (Layout- & Section-Aware PDF Ingestion)
- **Bộ đôi `PyMuPDF4LLM` + `RapidOCR`**: Chuyển đổi PDF học thuật đa cột phức tạp, bảng biểu và công thức sang Markdown có cấu trúc.
- **`SectionAwareChunker`**: Nhận diện và phân đoạn theo các mục chuẩn của bài báo (`Abstract`, `Introduction`, `Methodology`, `Experiments`, `Conclusion`), tự động loại bỏ tạp âm từ phần `References`/`Bibliography`.
- **Nạp nguồn đa dạng**: Tìm kiếm và nạp bài báo tự động theo từ khóa / ID từ **ArXiv** (kèm cơ chế dự phòng **OpenAlex** khi chạm giới hạn 429) hoặc **Tải file PDF từ máy tính**.

### 4. 🎯 Tìm kiếm Lai (Hybrid Search) & Reranking ONNX
- **Dense Vector Search**: Sử dụng vector database **Qdrant** kết hợp mô hình embedding ONNX `BAAI/bge-small-en-v1.5` (`FastEmbedder`).
- **Sparse Lexical Search**: Thuật toán `BM25Okapi` với tokenizer chuyên dụng bảo toàn các thuật ngữ học thuật (như `4-bit`, `NF4`, `bge-m3`).
- **Reciprocal Rank Fusion (RRF) & Cross-Encoder Reranker**: Hợp nhất danh sách ứng viên và chấm điểm lại bằng mô hình neural cross-encoder `Xenova/ms-marco-MiniLM-L-6-v2` chạy trên ONNX Runtime siêu nhanh.

### 5. 🕸️ Đồ thị Trích dẫn Tri thức (Citation Graph)
- Xây dựng đồ thị có hướng qua **NetworkX** kết hợp siêu dữ liệu trích dẫn từ OpenAlex.
- Phân tích các công trình đồng trích dẫn (*co-citation*) và ghép cặp thư mục (*bibliographic coupling*) để phát hiện các bài báo nền tảng liên quan.

### 6. 🛡️ Quy trình Agentic RAG 4 Giai đoạn & Kiểm định Trích dẫn
1. `decompose_query`: Tách câu hỏi so sánh phức tạp thành các câu hỏi con trọng tâm.
2. `retrieve_evidence`: Truy xuất lai đa truy vấn kết hợp thông tin lân cận từ đồ thị trích dẫn.
3. `synthesize_answer`: Tổng hợp câu trả lời có trích dẫn chi tiết theo định dạng `[paper_id: Section, p.X]`.
4. `verify_grounding`: Tấm khiên chống ảo giác (*Hallucination Guard*) kiểm tra đối chiếu từng thẻ trích dẫn với các đoạn văn bản thực tế trong cơ sở dữ liệu.

### 7. 🌐 Đa ngôn ngữ & Giao diện Tối ưu
- Hỗ trợ chuyển đổi song ngữ tức thì: **Tiếng Việt 🇻🇳** và **English 🇬🇧**.
- Hỗ trợ 2 chế độ màu **Dark / Light** dịu mắt.
- Cấu trúc frontend được module hóa sạch sẽ:
  ```
  app/
  ├── index.html            # Giao diện HTML thuần, trực quan, gọn gàng
  └── static/
      ├── css/              # tokens.css, base.css, components.css, markdown.css
      └── js/               # state.js, api.js, i18n.js, theme.js, ui.js,
                            # sources.js, chat.js, markdown-editor.js, main.js
  ```

---

## 📂 Cấu trúc Dự án

```
ScholarRAG/
├── app/
│   ├── index.html                  # Giao diện web chính
│   ├── server.py                   # FastAPI backend server
│   └── static/
│       ├── css/                    # Modular CSS (tokens, base, components, markdown)
│       └── js/                     # Modular JS (state, api, i18n, theme, ui, chat, editor...)
├── src/
│   ├── agent/                      # Agentic workflow, LLM client, prompt templates
│   ├── config.py                   # Quản lý cài đặt tập trung (Pydantic Settings)
│   ├── indexing/                   # Vector store (Qdrant), Citation Graph (NetworkX)
│   ├── ingestion/                  # PDF parsing (PyMuPDF4LLM + OCR), Section Chunker
│   ├── models/                     # Data schemas & validation
│   └── retrieval/                  # Hybrid retriever (Dense + BM25) & ONNX Reranker
├── data/                           # Thư mục lưu trữ PDF, parsed Markdown, Vector DB, Graph
├── tests/                          # Bộ unit test & integration test
├── cli.py                          # Giao diện dòng lệnh (CLI)
├── docker-compose.yml              # Cấu hình container Qdrant Server
├── pyproject.toml / requirements.txt
└── .env.example                    # File mẫu biến môi trường
```

---

## 🚀 Hướng dẫn Cài đặt & Khởi chạy

### 1. Chuẩn bị môi trường
Yêu cầu: **Python 3.10+**.

```bash
# Tạo và kích hoạt môi trường ảo
python3 -m venv .venv

# Kích hoạt trên Bash / Zsh:
source .venv/bin/activate

# Hoặc kích hoạt trên Fish Shell:
source .venv/bin/activate.fish

# Cài đặt các thư viện cần thiết
pip install -r requirements.txt
```

### 2. Thiết lập Biến môi trường
Sao chép file mẫu `.env.example` thành `.env` và điền cấu hình:
```bash
cp .env.example .env
```

Một số cấu hình chính trong `.env`:
```ini
# Lựa chọn LLM Provider: gemini, openai, deepseek, groq, openrouter, ollama, custom
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash

# API Keys tương ứng (hoặc điền trực tiếp trên Web UI)
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Tùy chọn Qdrant Server (Docker). Để trống nếu muốn chạy Local Disk.
QDRANT_URL=
```

### 3. (Tùy chọn) Chạy Qdrant Server qua Docker
Nếu muốn chạy Qdrant trong Docker thay vì lưu trữ cục bộ:
```bash
docker compose up -d
# Sau đó thiết lập QDRANT_URL=http://localhost:6333 trong file .env
```

### 4. Khởi động Web Application
```bash
uvicorn app.server:app --reload --port 8000
```
- Mở trình duyệt tại: **http://localhost:8000**
- Xem tài liệu API tự động (Swagger): **http://localhost:8000/docs**

---

## 💻 Sử dụng qua Giao diện Dòng lệnh (CLI)

Hệ thống cung cấp công cụ `cli.py` mạnh mẽ phục vụ tự động hóa và thử nghiệm:

```bash
# 1. Tải và phân tích bài báo từ ArXiv
python cli.py ingest -q "3D Gaussian Splatting" -n 2

# 2. Tự động đồng bộ các file PDF đã copy vào thư mục data/raw_pdfs/
python cli.py sync-local

# 3. Đặt câu hỏi nghiên cứu / so sánh (hỗ trợ các mode: hybrid, dense, sparse)
python cli.py ask -q "Làm thế nào 3D Gaussian Splatting đạt được tốc độ render thời gian thực?" --mode hybrid

# 4. Xem thống kê thư viện, số phân đoạn và đồ thị trích dẫn
python cli.py stats

# 5. Đánh lại chỉ mục embedding cho toàn bộ dữ liệu đã có
python cli.py reindex

# 6. Chạy đánh giá định lượng đối sánh (Ablation Benchmark: Dense vs BM25 vs Hybrid)
python cli.py eval
```

---

## 🧪 Kiểm thử (Testing)

Chạy bộ kiểm thử tự động với `pytest`:
```bash
pytest tests/
```
Toàn bộ các bài kiểm thử cho Ingestion, Hybrid Retrieval, Citation Graph, Agent Workflow và API endpoints đều được tích hợp sẵn.
