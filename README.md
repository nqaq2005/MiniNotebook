# MiniNotebook

**Trợ lý nghiên cứu khoa học và sổ tay Markdown dựa trên Agentic & Section-Aware Hybrid RAG**

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/FastAPI-0.112+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Qdrant-Vector%20Database-DC2626?style=for-the-badge&logo=qdrant&logoColor=white" alt="Qdrant" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License" />
</p>

MiniNotebook là hệ thống hỗ trợ đọc hiểu, đối chiếu và tổng hợp tài liệu, đồng thời tích hợp không gian ghi chú **Markdown** lấy cảm hứng từ **Obsidian**.

---

## Mục lục

- [Cài đặt và khởi chạy](#cài-đặt-và-khởi-chạy)
  - [Phương án 1: Docker Compose (khuyến nghị)](#phương-án-1-docker-compose-khuyến-nghị)
  - [Phương án 2: Môi trường Python cục bộ](#phương-án-2-môi-trường-python-cục-bộ)
- [Giao diện dòng lệnh (CLI)](#giao-diện-dòng-lệnh-cli)
- [Tính năng chính](#tính-năng-chính)
- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
- [Phím tắt](#phím-tắt)
- [Cấu trúc dự án](#cấu-trúc-dự-án)

- [Kiểm thử](#kiểm-thử)
- [Giấy phép và ghi nhận](#giấy-phép-và-ghi-nhận)

---

## Cài đặt và khởi chạy

### Phương án 1: Docker Compose (khuyến nghị)

Docker Compose đóng gói toàn bộ hệ thống, gồm **FastAPI Web App** và **Qdrant Vector Database**.

```bash
# 1. Tạo tệp cấu hình từ tệp mẫu
cp .env.example .env

# 2. Build và khởi động toàn bộ dịch vụ
docker compose up -d
```

Sau khi khởi động, truy cập các địa chỉ sau:

| Dịch vụ | Địa chỉ |
| :--- | :--- |
| Giao diện web MiniNotebook | <http://localhost:8000> |
| Qdrant Dashboard | <http://localhost:6333/dashboard> |
| Tài liệu API (Swagger) | <http://localhost:8000/docs> |

### Phương án 2: Môi trường Python cục bộ

**Yêu cầu**: Python 3.11 trở lên.

**1. Chuẩn bị môi trường**

```bash
# Tạo và kích hoạt môi trường ảo
python3 -m venv .venv
source .venv/bin/activate

# Cài đặt thư viện phụ thuộc
pip install -r requirements.txt
```

**2. Cấu hình biến môi trường**

```bash
cp .env.example .env
```

**3. Khởi động ứng dụng**

```bash
# (Tùy chọn) Chạy riêng Qdrant Server bằng Docker
docker compose up -d qdrant

# Khởi động server Uvicorn
uvicorn app.server:app --reload --port 8000
```

Truy cập ứng dụng tại <http://localhost:8000>.

---

## Giao diện dòng lệnh (CLI)

Công cụ `cli.py` phục vụ tự động hóa và chạy thử nghiệm hàng loạt:

```bash
# Tải và lập chỉ mục bài báo từ ArXiv theo từ khóa hoặc ID
python cli.py ingest -q "3D Gaussian Splatting" -n 2

# Đồng bộ các tệp PDF đã đặt trong data/raw_pdfs/
python cli.py sync-local

# Đặt câu hỏi nghiên cứu hoặc đối chiếu (chế độ: hybrid, dense, sparse)
python cli.py ask -q "Làm thế nào 3D Gaussian Splatting đạt tốc độ render thời gian thực?" --mode hybrid

# Xem thống kê thư viện, số phân đoạn và đồ thị trích dẫn
python cli.py stats

# Lập lại chỉ mục embedding cho toàn bộ dữ liệu hiện có
python cli.py reindex

# Chạy đánh giá định lượng (Ablation Benchmark: Dense vs BM25 vs Hybrid)
python cli.py eval
```

---


## Tính năng chính

### 1. Sổ tay Markdown song song với khung hỏi đáp

- **Soạn thảo cạnh khung chat**: ghi chú ý tưởng và tóm tắt tài liệu ngay bên cạnh phần hỏi đáp.
- **Hai chế độ hiển thị**:
  - *Split mode*: đặt song song với khung chat để vừa đọc câu trả lời vừa ghi chép.
  - *Overlay mode*: phủ toàn bộ khu vực chat, giữ nguyên thanh nguồn bên trái, kèm hiệu ứng chuyển cảnh FLIP.
- **Ba chế độ xem**: chỉ soạn thảo (*Editor only*), chia đôi xem trước (*Split view*) và xem trước tài liệu (*Preview document*).
- **Chèn vào Markdown**: nút dưới mỗi câu trả lời của AI giúp đưa nội dung tổng hợp cùng trích dẫn vào bản ghi chú chỉ với một thao tác.
- **Tiện ích soạn thảo**: phím tắt định dạng (`Ctrl+B`, `Ctrl+I`, `Tab`), mẫu bảng, thống kê từ/ký tự/dòng theo thời gian thực, tải xuống tệp `.md`, sao chép nhanh và tự động lưu qua `localStorage`.

### 2. Xử lý tài liệu theo bố cục và cấu trúc mục

- **`PyMuPDF4LLM` + `RapidOCR`**: chuyển đổi PDF học thuật nhiều cột, bảng biểu và công thức toán sang Markdown có cấu trúc.
- **`SectionAwareChunker`**: nhận diện và phân đoạn theo các mục chuẩn của bài báo (`Abstract`, `Introduction`, `Methodology`, `Experiments`, `Conclusion`), đồng thời loại bỏ nhiễu từ phần `References`/`Bibliography`.
- **Nguồn nạp tài liệu**: tìm kiếm và nạp bài báo từ **ArXiv** theo từ khóa hoặc ID (tự động chuyển sang **OpenAlex** khi gặp giới hạn 429), hoặc tải tệp PDF từ máy tính.

### 3. Quy trình Agentic RAG bốn giai đoạn và kiểm định trích dẫn

1. `decompose_query`: tách câu hỏi so sánh phức tạp thành các câu hỏi con (hỗ trợ tiếng Việt và tiếng Anh).
2. `retrieve_evidence`: truy xuất lai đa truy vấn, kết hợp thông tin cấu trúc mục của bài báo.
3. `synthesize_answer`: tổng hợp câu trả lời kèm trích dẫn theo định dạng `[paper_id: Section, p.X]`.
4. `verify_grounding`: kiểm định tính có căn cứ (*Grounding & Citation Guard*), đối chiếu tính hợp lệ của thẻ trích dẫn và đo mức trùng khớp từ vựng (*lexical evidence overlap*) giữa câu trả lời với các đoạn ngữ cảnh đã truy xuất.


---

## Kiến trúc hệ thống

<img width="2400" height="1792" alt="architecture" src="https://github.com/user-attachments/assets/f45b2295-bbe4-4bd6-b757-0892eb67f044" />

---

## Phím tắt

Các phím tắt toàn cục tự động ngăn hành vi mặc định của trình duyệt (`e.preventDefault()`).

| Phím tắt | Chức năng | Mô tả |
| :--- | :--- | :--- |
| `Ctrl + M` | Đóng/mở ghi chú Markdown | Bật hoặc tắt khung soạn thảo từ bất kỳ vị trí nào, kể cả khi đang nhập văn bản. |
| `Ctrl + Shift + S` | Đóng/mở tab Nguồn tài liệu | Thu gọn hoặc mở rộng thanh danh sách bài báo bên trái (chặn phím tắt chụp màn hình của trình duyệt). |
| `Ctrl + I` | Đóng/mở Cài đặt | Mở hộp thoại tùy chỉnh mô hình LLM, Base URL, chế độ suy luận và ngôn ngữ (chặn hộp thoại Page Info). |
| `Ctrl + B` | In đậm văn bản | Chèn cú pháp `**văn bản**` trong ô soạn thảo ghi chú. |
| `Tab` | Thụt lề văn bản | Thêm 2 dấu cách mà không làm mất focus khỏi khung soạn thảo. |
| `Esc` | Đóng nhanh hộp thoại/Drawer | Đóng hộp thoại cài đặt, khung xem chi tiết nguồn hoặc menu thả xuống. |

---

## Cấu trúc dự án

```
MiniNotebook/
├── app/
│   ├── index.html                  # Giao diện web chính (HTML5 + Tailwind CSS)
│   ├── server.py                   # FastAPI server (endpoints, healthz, NDJSON streaming)
│   └── static/
│       ├── css/                    # CSS theo module (tokens, base, components, markdown)
│       └── js/                     # JS theo module (state, api, i18n, theme, ui, chat, editor, ...)
├── src/
│   ├── agent/                      # Agentic workflow, LLM client, định tuyến, prompt templates
│   ├── config.py                   # Quản lý cấu hình tập trung (Pydantic BaseSettings)
│   ├── indexing/                   # Vector store (Qdrant), đồ thị trích dẫn (NetworkX)
│   ├── ingestion/                  # Phân tích PDF (PyMuPDF4LLM + OCR), Section Chunker, ArXiv fetcher
│   ├── models/                     # Schema dữ liệu và validation (RetrievedPassage, SectionChunk)
│   ├── retrieval/                  # Hybrid retriever (Dense + BM25) và ONNX Reranker
│   └── evaluation/                 # Pipeline đánh giá định lượng (Ablation Benchmark)
├── data/                           # Dữ liệu lưu trữ (mount qua Docker Volume)
│   ├── raw_pdfs/                   # Tệp PDF gốc
│   ├── parsed_md/                  # Markdown đã trích xuất cấu trúc
│   ├── vector_db/                  # Vector storage cục bộ (dự phòng)
│   ├── models_cache/               # Cache trọng số ONNX của embedding và reranker
│   ├── citation_graph/             # Đồ thị trích dẫn (graph.json)
│   └── qdrant_server_storage/      # Dữ liệu của Qdrant Server (Docker)
├── tests/                          # Unit test và integration test (15 test suite)
├── cli.py                          # Giao diện dòng lệnh
├── Dockerfile                      # Multi-layer build trên Python 3.11-slim
├── .dockerignore                   # Danh sách loại trừ khi build Docker
├── docker-compose.yml              # Điều phối Web App và Qdrant
├── pyproject.toml / requirements.txt
└── .env.example                    # Mẫu biến môi trường
```

---
## Kiểm thử

Bộ kiểm thử tự động bao quát Ingestion, Hybrid Retrieval, Citation Graph, Agent Workflow và các API endpoint:

```bash
# Chạy toàn bộ test suite
pytest tests/

# Kiểm tra cú pháp JavaScript
node -c app/static/js/*.js
```

---

## Giấy phép và ghi nhận

- **Giấy phép phần mềm**: dự án được phát hành theo [MIT License](./LICENSE), cho phép sử dụng, chỉnh sửa, phân phối và tích hợp vào các dự án học tập, nghiên cứu hoặc thương mại.
- **Phát triển độc lập (clean-room)**: dự án được xây dựng từ đầu bằng Python/FastAPI và HTML/Tailwind/JavaScript thuần, không sao chép mã nguồn đóng từ bất kỳ dịch vụ thương mại nào.
- **Font chữ**: giao diện sử dụng **Plus Jakarta Sans** và **Inter**, được cấp phép theo **SIL Open Font License (OFL)**, miễn phí cho mọi mục đích sử dụng.
