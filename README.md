# 🎓 MiniNotebook — Trợ lý Nghiên cứu Khoa học & Sổ tay Markdown

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/FastAPI-0.112+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Qdrant-Vector%20Database-DC2626?style=for-the-badge&logo=qdrant&logoColor=white" alt="Qdrant" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License" />
</p>

**MiniNotebook** là hệ thống **Agentic & Section-Aware Hybrid RAG** hiện đại được thiết kế phục vụ việc nghiên cứu, đọc hiểu, đối chiếu và tổng hợp tài liệu khoa học theo phong cách **NotebookLM**, kết hợp không gian soạn thảo ghi chú **Markdown** lấy cảm hứng từ **Obsidian**.

---

## 📑 Mục lục
- [✨ Điểm nổi bật & Tính năng cốt lõi](#-điểm-nổi-bật--tính-năng-cốt-lõi)
- [🏗️ Kiến trúc Hệ thống](#️-kiến-trúc-hệ-thống)
- [⌨️ Bảng Phím tắt Thao tác nhanh](#️-bảng-phím-tắt-thao-tác-nhanh)
- [📂 Cấu trúc Dự án](#-cấu-trúc-dự-án)
- [🚀 Hướng dẫn Cài đặt & Khởi chạy](#-hướng-dẫn-cài-đặt--khởi-chạy)
  - [Cách 1: Khởi động trọn gói bằng Docker Compose (Khuyên dùng)](#cách-1-khởi-động-trọn-gói-bằng-docker-compose-khuyên-dùng)
  - [Cách 2: Khởi động thủ công trên máy cục bộ (Local Python)](#cách-2-khởi-động-thủ-công-trên-máy-cục-bộ-local-python)
- [💻 Sử dụng qua Giao diện Dòng lệnh (CLI)](#-sử-dụng-qua-giao-diện-dòng-lệnh-cli)
- [🧪 Kiểm thử Hệ thống (Testing)](#-kiểm-thử-hệ-thống-testing)
- [🛡️ Bản quyền & Font chữ Mã nguồn mở](#️-bản-quyền--font-chữ-mã-nguồn-mở)

---

## ✨ Điểm nổi bật & Tính năng cốt lõi

### 1. 📝 Sổ tay Markdown Song song (Obsidian-Inspired)
- **Soạn thảo linh hoạt song song với Chat**: Ghi chú ý tưởng, tóm tắt tài liệu ngay cạnh khung hỏi đáp.
- **2 Chế độ hiển thị thông minh**:
  - **Chia đôi màn hình (Split mode)**: Đặt song song với khung chat để vừa đọc câu trả lời vừa ghi chép.
  - **Phủ toàn bộ (Overlay mode)**: Mở rộng phủ trọn khu vực chat (vẫn giữ nguyên thanh nguồn bên trái) với hiệu ứng chuyển cảnh FLIP mượt mà.
- **3 Chế độ xem**: Chỉ soạn thảo (*Editor only*), Chia đôi xem trước (*Split view*), Xem trước tài liệu (*Preview document*).
- **1-Click "Chèn vào Markdown"**: Nút tiện ích dưới mỗi câu trả lời AI giúp đưa nội dung tổng hợp và trích dẫn chuẩn xác thẳng vào bản ghi chú.
- **Tiện ích đầy đủ**: Phím tắt định dạng (`Ctrl+B`, `Ctrl+I`, `Tab`), mẫu bảng biểu, đếm từ/ký tự/dòng theo thời gian thực, tải file `.md`, sao chép nhanh và tự động lưu `localStorage`.

### 2. ⚡ Đa dạng Nhà cung cấp LLM (Multi-Provider Support)
Hệ thống hỗ trợ toàn diện các nền tảng LLM hàng đầu với khả năng streaming token tức thì:
- **Google Gemini**: Gọi native REST API (`gemini-2.5-flash`, `gemini-1.5-pro`, v.v.), hỗ trợ cấu hình ngân sách suy luận (*thinking budget*).
- **OpenAI**: Chuẩn `/v1/chat/completions` (`gpt-4o`, `gpt-4o-mini`, `o1`, `o3-mini`) kèm tham số `reasoning_effort`.
- **DeepSeek**: Hỗ trợ `deepseek-chat` (V3) và `deepseek-reasoner` (R1) — tự động bắt trường `reasoning_content` để hiển thị hộp suy luận riêng.
- **Groq**: Streaming siêu tốc với `llama-3.3-70b-versatile`, `deepseek-r1-distill-llama-70b`.
- **OpenRouter**: Truy cập hàng trăm mô hình mã nguồn mở và thương mại qua một API key duy nhất.
- **Ollama / vLLM**: Chạy offline 100% trên máy cục bộ (`localhost`), không bắt buộc API key, có bộ định tuyến `_ThinkTagRouter` tự động bóc tách thẻ `<think>...</think>`.
- **Custom Endpoint**: Tùy biến mọi Base URL (LM Studio, LocalAI, Cloudflare Tunnel, LiteLLM).
- **Extractive Mode (Fallback dự phòng)**: Khi không có API key hoặc mất mạng, hệ thống tự động trích xuất các đoạn trích điểm cao nhất từ cơ sở dữ liệu để tổng hợp câu trả lời mà không bị gián đoạn.

### 3. 🔬 Xử lý Tài liệu Chuyên sâu (Layout- & Section-Aware PDF Ingestion)
- **Bộ đôi `PyMuPDF4LLM` + `RapidOCR`**: Chuyển đổi PDF học thuật đa cột phức tạp, bảng biểu và công thức toán sang Markdown có cấu trúc.
- **`SectionAwareChunker`**: Nhận diện và phân đoạn theo các mục chuẩn của bài báo (`Abstract`, `Introduction`, `Methodology`, `Experiments`, `Conclusion`), tự động loại bỏ tạp âm từ phần `References`/`Bibliography`.
- **Nạp nguồn đa dạng**: Tìm kiếm và nạp bài báo tự động theo từ khóa / ID từ **ArXiv** (kèm cơ chế dự phòng **OpenAlex** khi chạm giới hạn 429) hoặc **Tải file PDF từ máy tính**.

### 4. 🎯 Tìm kiếm Lai (Hybrid Search) & Reranking ONNX
- **Dense Vector Search**: Sử dụng vector database **Qdrant** kết hợp mô hình embedding ONNX `BAAI/bge-small-en-v1.5` (`FastEmbedder`).
- **Sparse Lexical Search**: Thuật toán `BM25Okapi` với tokenizer chuyên dụng bảo toàn các thuật ngữ học thuật (như `4-bit`, `NF4`, `bge-m3`, `LoRA`).
- **Reciprocal Rank Fusion (RRF) & Cross-Encoder Reranker**: Hợp nhất danh sách ứng viên và chấm điểm lại bằng mô hình neural cross-encoder `Xenova/ms-marco-MiniLM-L-6-v2` chạy trên ONNX Runtime với độ trễ thấp.

### 5. 🛡️ Quy trình Agentic RAG 4 Giai đoạn & Kiểm định Trích dẫn
1. `decompose_query`: Tách câu hỏi so sánh phức tạp thành các câu hỏi con trọng tâm (hỗ trợ cả tiếng Việt và tiếng Anh).
2. `retrieve_evidence`: Truy xuất lai đa truy vấn kết hợp thông tin cấu trúc mục bài báo.
3. `synthesize_answer`: Tổng hợp câu trả lời có trích dẫn chi tiết theo định dạng `[paper_id: Section, p.X]`.
4. `verify_grounding`: Kiểm định tính có căn cứ (*Grounding & Citation Guard*) đối chiếu tính hợp lệ của thẻ trích dẫn và đo độ trùng khớp từ vựng (*lexical evidence overlap*) giữa câu trả lời với các đoạn trích context trong cơ sở dữ liệu.

### 6. 🌐 Đa ngôn ngữ & Giao diện Tối ưu
- Hỗ trợ chuyển đổi song ngữ tức thì: **Tiếng Việt 🇻🇳** và **English 🇬🇧**.
- Hỗ trợ 2 chế độ màu **Dark / Light** dịu mắt.
- Sử dụng typography mã nguồn mở **Plus Jakarta Sans** & **Inter** (SIL Open Font License).

---

## 🏗️ Kiến trúc Hệ thống

<img width="2400" height="1792" alt="architecture" src="https://github.com/user-attachments/assets/f45b2295-bbe4-4bd6-b757-0892eb67f044" />


---

## ⌨️ Bảng Phím tắt Thao tác nhanh

Hệ thống được trang bị các tổ hợp phím tắt toàn cục, tự động ngăn chặn các hành vi trùng lặp của trình duyệt (`e.preventDefault()`):

| Phím tắt               | Chức năng                        | Mô tả chi tiết                                                                                    |
| :--------------------- | :------------------------------- | :------------------------------------------------------------------------------------------------ |
| **`Ctrl + M`**         | **Đóng / Mở Ghi chú Markdown**   | Bật hoặc tắt nhanh khung soạn thảo Markdown từ bất kỳ đâu (kể cả khi đang gõ text).               |
| **`Ctrl + Shift + S`** | **Đóng / Mở Tab Nguồn tài liệu** | Thu gọn hoặc mở rộng thanh danh sách bài báo bên trái (chặn phím tắt chụp màn hình trình duyệt).  |
| **`Ctrl + I`**         | **Đóng / Mở Cài đặt (Settings)** | Mở modal tùy chỉnh mô hình LLM, Base URL, chế độ suy luận và ngôn ngữ (chặn hộp thoại Page Info). |
| **`Ctrl + B`**         | **In đậm văn bản (Markdown)**    | Chèn cú pháp in đậm `**văn bản**` trong ô soạn thảo ghi chú.                                      |
| **`Tab`**              | **Thụt lề văn bản (Markdown)**   | Thêm 2 dấu cách thụt lề chuẩn mà không làm mất focus khỏi khung soạn thảo.                        |
| **`Esc`**              | **Đóng nhanh modal / Drawer**    | Đóng hộp thoại cài đặt, xem chi tiết nguồn hoặc menu thả xuống.                                   |

---

## 📂 Cấu trúc Dự án

```
MiniNotebook/
├── app/
│   ├── index.html                  # Giao diện web chính (HTML5 + Tailwind CSS + Typography)
│   ├── server.py                   # FastAPI backend server (Endpoints, Healthz, NDJSON Streaming)
│   └── static/
│       ├── css/                    # Modular CSS (tokens.css, base.css, components.css, markdown.css)
│       └── js/                     # Modular JS (state, api, i18n, theme, ui, chat, editor...)
├── src/
│   ├── agent/                      # Agentic workflow, LLM client, routing, prompt templates
│   ├── config.py                   # Quản lý cài đặt tập trung (Pydantic BaseSettings)
│   ├── indexing/                   # Vector store (Qdrant), Citation Graph (NetworkX)
│   ├── ingestion/                  # PDF parsing (PyMuPDF4LLM + OCR), Section Chunker, ArXiv fetcher
│   ├── models/                     # Data schemas & validation (RetrievedPassage, SectionChunk)
│   ├── retrieval/                  # Hybrid retriever (Dense + BM25) & ONNX Reranker
│   └── evaluation/                 # Pipeline đánh giá định lượng đối sánh (Ablation Benchmark)
├── data/                           # Dữ liệu lưu trữ (được mount qua Docker Volume)
│   ├── raw_pdfs/                   # File PDF gốc nạp vào
│   ├── parsed_md/                  # Markdown bài báo đã trích xuất cấu trúc
│   ├── vector_db/                  # Local vector storage (fallback)
│   ├── models_cache/               # Cache trọng số ONNX của mô hình embedding & reranker
│   ├── citation_graph/             # Đồ thị trích dẫn (graph.json)
│   └── qdrant_server_storage/      # Thư mục lưu trữ của Qdrant Server Docker
├── tests/                          # Bộ unit test & integration test toàn diện (15 test suites)
├── cli.py                          # Giao diện dòng lệnh (CLI)
├── Dockerfile                      # Dockerfile tối ưu multi-layer với Python 3.11-slim
├── .dockerignore                   # Danh sách loại trừ context build Docker
├── docker-compose.yml              # Điều phối trọn gói container Web App & Qdrant Database
├── pyproject.toml / requirements.txt
└── .env.example                    # File mẫu biến môi trường
```

---

## 🚀 Hướng dẫn Cài đặt & Khởi chạy

### Cách 1: Khởi động trọn gói bằng Docker Compose (Khuyên dùng)

Toàn bộ hệ sinh thái (bao gồm **FastAPI Web App** và **Qdrant Vector Database**) được đóng gói sẵn trong Docker Compose:

```bash
# 1. Tạo file cấu hình từ file mẫu (nếu chưa có)
cp .env.example .env

# 2. Khởi động cả ứng dụng và Qdrant chỉ với 1 câu lệnh:
docker compose up -d --build

# 3. Theo dõi log thời gian thực:
docker compose logs -f

# 4. Kiểm tra trạng thái các container:
docker compose ps
```

* **Giao diện Web MiniNotebook**: [http://localhost:8000](http://localhost:8000)
* **Bảng điều khiển Qdrant Web Dashboard**: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)
* **Tài liệu API tự động (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)

> [!TIP]
> **Tại sao nên dùng cờ `--build`?**
> Cờ `--build` đảm bảo Docker sẽ quét và đóng gói lại toàn bộ mã nguồn mới nhất bạn vừa chỉnh sửa. Nhờ cơ chế Layer Cache, quá trình này chỉ mất 2-3 giây. Nếu không sửa code mà chỉ bật lại hệ thống, bạn chỉ cần gõ `docker compose up -d`.

Để dừng hệ thống:
```bash
docker compose down
```

---

### Cách 2: Khởi động thủ công trên máy cục bộ (Local Python)

Nếu bạn muốn chạy trực tiếp bằng môi trường Python trên máy host:

#### 1. Chuẩn bị môi trường Python 3.11+
```bash
# Tạo và kích hoạt môi trường ảo
python3 -m venv .venv
source .venv/bin/activate

# Cài đặt thư viện phụ thuộc
pip install -r requirements.txt
```

#### 2. Thiết lập Biến môi trường
```bash
cp .env.example .env
```
Chỉnh sửa file `.env` với các thông số mong muốn:
```ini
# LLM Provider: gemini, openai, deepseek, groq, openrouter, ollama, custom
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
GEMINI_API_KEY=your_gemini_api_key_here

# Để trống QDRANT_URL nếu muốn chạy Local Disk trên host, 
# hoặc đặt http://localhost:6333 nếu chạy Qdrant Docker riêng
QDRANT_URL=
```

#### 3. Khởi động ứng dụng
```bash
# (Tùy chọn) Chạy riêng container Qdrant nếu muốn dùng Qdrant Server:
docker compose up -d qdrant

# Khởi chạy server Uvicorn:
uvicorn app.server:app --reload --port 8000
```
Mở trình duyệt tại: **http://localhost:8000**

---

## 💻 Sử dụng qua Giao diện Dòng lệnh (CLI)

MiniNotebook cung cấp công cụ `cli.py` mạnh mẽ phục vụ tự động hóa và thử nghiệm hàng loạt:

```bash
# 1. Tải và lập chỉ mục bài báo từ ArXiv theo từ khóa hoặc ID
python cli.py ingest -q "3D Gaussian Splatting" -n 2

# 2. Tự động đồng bộ các file PDF đã copy vào thư mục data/raw_pdfs/
python cli.py sync-local

# 3. Đặt câu hỏi nghiên cứu / đối chiếu (chế độ: hybrid, dense, sparse)
python cli.py ask -q "Làm thế nào 3D Gaussian Splatting đạt tốc độ render thời gian thực?" --mode hybrid

# 4. Xem thống kê thư viện, số phân đoạn và đồ thị trích dẫn
python cli.py stats

# 5. Đánh lại chỉ mục embedding cho toàn bộ dữ liệu đã có
python cli.py reindex

# 6. Chạy đánh giá định lượng đối sánh (Ablation Benchmark: Dense vs BM25 vs Hybrid)
python cli.py eval
```

---

## 🧪 Kiểm thử Hệ thống (Testing)

Dự án đi kèm bộ kiểm thử tự động toàn diện bao quát Ingestion, Hybrid Retrieval, Citation Graph, Agent Workflow và API endpoints:

```bash
# Chạy toàn bộ test suites với pytest:
pytest tests/

# Kiểm tra cú pháp JavaScript:
node -c app/static/js/*.js
```

---

## 🛡️ Bản quyền & Giấy phép (License)

* **Giấy phép phần mềm**: Dự án được phát hành dưới giấy phép mã nguồn mở [MIT License](file:///home/nqaq2005/Projects/RAG/LICENSE). Bạn hoàn toàn có quyền sử dụng, chỉnh sửa, phân phối và tích hợp vào các dự án học tập, nghiên cứu hoặc thương mại.
* **Clean-room Implementation**: Dự án được xây dựng từ đầu bằng Python/FastAPI và HTML/Tailwind/JS thuần, không sao chép mã nguồn đóng từ bất kỳ dịch vụ thương mại nào.
* **Typography**: Giao diện sử dụng bộ đôi font **Plus Jakarta Sans** và **Inter** — được cấp phép theo **SIL Open Font License (OFL)**, hoàn toàn miễn phí và an toàn cho mọi mục đích học tập, nghiên cứu và thương mại.
