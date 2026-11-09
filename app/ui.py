import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st

from src.agent.nodes import LLMClient
from src.agent.workflow import LiteratureReviewAgent
from src.config import settings
from src.evaluation.eval_pipeline import RAGEvaluator, build_dynamic_benchmark
from src.indexing.citation_graph import CitationGraphStore
from src.indexing.vector_store import HybridVectorStore
from src.ingestion.pipeline import IngestionPipeline
from src.retrieval.hybrid_retriever import HybridGraphRetriever


st.set_page_config(
    page_title="ScholarRAG — AI Literature Review Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2.5rem;
        max-width: 1280px;
    }
    .hero-card {
        background: linear-gradient(135deg, rgba(30, 58, 138, 0.12) 0%, rgba(15, 23, 42, 0.04) 100%);
        border: 1px solid rgba(99, 102, 241, 0.25);
        border-radius: 14px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.25rem;
    }
    .hero-title {
        font-size: 1.75rem;
        font-weight: 700;
        margin: 0 0 0.3rem 0;
    }
    .hero-subtitle {
        font-size: 0.96rem;
        opacity: 0.82;
        margin: 0;
    }
    .badge-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-top: 0.75rem;
    }
    .tech-badge {
        display: inline-block;
        padding: 0.2rem 0.65rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        background: rgba(99, 102, 241, 0.14);
        border: 1px solid rgba(99, 102, 241, 0.3);
    }
    .paper-card {
        border: 1px solid rgba(148, 163, 184, 0.25);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.85rem;
        background: rgba(255, 255, 255, 0.02);
    }
    .section-pill {
        display: inline-block;
        padding: 0.12rem 0.5rem;
        margin: 0.15rem 0.2rem 0.15rem 0;
        border-radius: 6px;
        font-size: 0.76rem;
        background: rgba(148, 163, 184, 0.15);
    }
</style>
"""

TOPIC_PRESETS = {
    "✍️ Nhập từ khóa hoặc mã ArXiv bất kỳ": "",
    "🤖 Agentic RAG & GraphRAG": "Agentic Retrieval Augmented Generation GraphRAG",
    "🎨 3D Gaussian Splatting & NeRF": "3D Gaussian Splatting real-time radiance field rendering",
    "🦾 Diffusion Policy & Robotics": "Diffusion Policy visuomotor robot manipulation",
    "👁️ Multimodal Vision-Language Models": "Vision Language Models multimodal instruction tuning",
    "🧠 Reasoning LLMs & Test-Time Compute": "Chain of Thought reasoning test-time compute scaling LLMs",
    "🧬 Protein Folding & Biomolecular AI": "AlphaFold protein structure prediction diffusion",
}


@st.cache_resource
def init_stores():
    vector_store = HybridVectorStore()
    citation_graph = CitationGraphStore()
    pipeline = IngestionPipeline(
        vector_store=vector_store,
        citation_graph=citation_graph,
    )
    return vector_store, citation_graph, pipeline


def build_citation_dot_graph(citation_graph: CitationGraphStore, max_external: int = 25) -> str:
    """Build a Graphviz DOT string visualizing ingested papers and their shared citations."""
    lines = [
        "digraph CitationGraph {",
        '  graph [rankdir=LR, bgcolor="transparent", pad="0.3", nodesep="0.4", ranksep="0.8"];',
        '  node [fontname="Sans-Serif", fontsize=10, style="filled,rounded", shape=box];',
        '  edge [color="#64748b", arrowsize=0.7];',
    ]

    ingested_ids = [
        n for n, attr in citation_graph.graph.nodes(data=True) if attr.get("ingested", False)
    ]
    for pid in ingested_ids:
        title = citation_graph.graph.nodes[pid].get("title", pid)
        short_title = (title[:38] + "...") if len(title) > 41 else title
        safe_label = f"[{pid}]\\n{short_title}".replace('"', "'")
        lines.append(
            f'  "{pid}" [label="{safe_label}", fillcolor="#DBEAFE", color="#2563EB", fontcolor="#1E3A8A"];'
        )

    # Prioritize external references cited by >= 2 ingested papers, then top cited
    ext_Zero_or_more = []
    for n, attr in citation_graph.graph.nodes(data=True):
        if not attr.get("ingested", False):
            in_deg = citation_graph.graph.in_degree(n)
            if in_deg > 0:
                ext_Zero_or_more.append((in_deg, n))
    ext_Zero_or_more.sort(reverse=True)

    kept_ext = {n for _, n in ext_Zero_or_more[:max_external]}
    for in_deg, ext_id in ext_Zero_or_more[:max_external]:
        fill = "#FEF3C7" if in_deg >= 2 else "#F1F5F9"
        border = "#D97706" if in_deg >= 2 else "#94A3B8"
        font = "#78350F" if in_deg >= 2 else "#334155"
        tag = f"Shared Ref\\n{ext_id}" if in_deg >= 2 else ext_id
        lines.append(
            f'  "{ext_id}" [label="{tag}", shape=ellipse, fontsize=9, fillcolor="{fill}", color="{border}", fontcolor="{font}"];'
        )

    for u, v in citation_graph.graph.edges():
        if u in ingested_ids and (v in ingested_ids or v in kept_ext):
            lines.append(f'  "{u}" -> "{v}";')

    lines.append("}")
    return "\n".join(lines)


def get_ingested_papers_list(citation_graph: CitationGraphStore, vector_store: HybridVectorStore):
    items = []
    for node_id, attr in citation_graph.graph.nodes(data=True):
        if attr.get("ingested", False):
            chunks = [c for c in vector_store.chunks_by_id.values() if c.paper_id == node_id]
            sections = list(dict.fromkeys(c.section_title for c in chunks))
            items.append(
                {
                    "paper_id": node_id,
                    "title": attr.get("title", node_id),
                    "authors": attr.get("authors", []),
                    "published_date": attr.get("published_date", "N/A"),
                    "citation_count": attr.get("citation_count", 0),
                    "out_refs": citation_graph.graph.out_degree(node_id),
                    "chunk_count": len(chunks),
                    "sections": sections,
                }
            )
    return items


def main():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    vector_store, citation_graph, pipeline = init_stores()

    if "qa_history" not in st.session_state:
        st.session_state.qa_history = []
    if "active_question" not in st.session_state:
        st.session_state.active_question = ""

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown("## 🎓 ScholarRAG")
        st.caption("AI Literature Review & Citation Graph Assistant")

        st.markdown("### 📥 1. Thêm bài báo khoa học")
        ingest_tab_arxiv, ingest_tab_pdf = st.tabs(["🔎 Tìm ArXiv", "📄 Tải PDF lên"])

        with ingest_tab_arxiv:
            preset_choice = st.selectbox(
                "Chủ đề gợi ý nhanh",
                options=list(TOPIC_PRESETS.keys()),
                index=0,
            )
            topic_query = st.text_input(
                "Từ khóa hoặc mã ArXiv ID",
                value=TOPIC_PRESETS[preset_choice],
                placeholder="VD: GraphRAG, 3D Gaussian Splatting, 2305.14314",
            )
            max_papers = st.slider("Số lượng bài báo tải về", min_value=1, max_value=8, value=2)

            if st.button("🚀 Tìm & Nạp vào Thư viện", type="primary", use_container_width=True):
                if not topic_query.strip():
                    st.warning("Vui lòng nhập từ khóa hoặc mã ArXiv ID.")
                else:
                    with st.spinner(f"Đang tìm '{topic_query}', phân tích bố cục PDF & tạo vector..."):
                        try:
                            stats = pipeline.ingest_topic(query=topic_query.strip(), max_papers=max_papers)
                            if stats["papers_ingested"] > 0:
                                st.success(
                                    f"Đã nạp {stats['papers_ingested']} bài báo ({stats['chunks_indexed']} phân đoạn)!"
                                )
                                st.rerun()
                            else:
                                st.warning("Không tìm thấy bài báo phù hợp. Hãy thử từ khóa khác.")
                        except Exception as exc:
                            st.error(f"Lỗi khi tải bài báo: {exc}")

        with ingest_tab_pdf:
            uploaded_file = st.file_uploader("Chọn file PDF từ máy tính", type=["pdf"])
            custom_pdf_title = st.text_input("Tiêu đề bài báo (Tùy chọn)", placeholder="Tự động nhận diện nếu để trống")
            if uploaded_file is not None and st.button("📥 Phân tích & Nạp PDF", type="primary", use_container_width=True):
                save_path = settings.raw_pdf_dir / uploaded_file.name
                save_path.write_bytes(uploaded_file.getvalue())
                with st.spinner(f"Đang phân tích '{uploaded_file.name}' với RapidOCR..."):
                    info = pipeline.ingest_local_pdf(
                        pdf_path=save_path,
                        title=custom_pdf_title.strip() or None,
                    )
                st.success(f"Đã nạp '{info['title']}' ({info['chunks_indexed']} phân đoạn)!")
                st.rerun()

        st.divider()
        with st.expander("⚙️ 2. Cấu hình Truy vấn & Mô hình LLM", expanded=False):
            search_mode = st.selectbox(
                "Chế độ Truy vấn (Retrieval Mode)",
                options=["hybrid", "dense", "sparse"],
                format_func=lambda m: {
                    "hybrid": "Hybrid (Qdrant Dense + BM25 + Rerank)",
                    "dense": "Dense Vector Only (BGE-Small ONNX)",
                    "sparse": "Sparse Lexical Only (BM25Okapi)",
                }[m],
                index=0,
            )

            provider_options = ["gemini", "custom"]
            default_provider_idx = 1 if settings.llm_provider.lower() == "custom" else 0
            llm_provider = st.selectbox(
                "Nhà cung cấp LLM",
                options=provider_options,
                format_func=lambda p: "Google Gemini API" if p == "gemini" else "Custom URL (OpenAI-Compatible / Proxy)",
                index=default_provider_idx,
            )

            custom_base_url = st.text_input(
                "Custom Base URL (Tùy chọn)",
                value=settings.llm_base_url,
                placeholder="VD: http://localhost:11434/v1",
            )

            llm_model = st.text_input(
                "Tên Model LLM",
                value=settings.llm_model,
                help="VD: gemini-2.5-flash, gpt-4o-mini, qwen2.5:7b",
            )

            default_key = (
                settings.custom_api_key or settings.openai_api_key or settings.gemini_api_key
                if llm_provider == "custom"
                else settings.gemini_api_key
            )
            if default_key in ("your_gemini_api_key_here", "your_openai_api_key_here", "your_custom_api_key_here"):
                default_key = ""

            api_key_input = st.text_input(
                "API Key",
                value=default_key,
                type="password",
                help="Tự động nạp từ file .env nếu đã cấu hình.",
            )

        llm_client = LLMClient(
            api_key=api_key_input,
            model_name=llm_model,
            provider=llm_provider,
            base_url=custom_base_url,
        )

        st.divider()
        st.caption(
            f"**Trạng thái LLM:** {'🟢 Đã kết nối (' + llm_model + ')' if llm_client.is_configured else '🟡 Chế độ trích xuất Offline'}  \n"
            f"**Vector Embedder:** `BAAI/bge-small-en-v1.5`  \n"
            f"**Cross-Encoder:** `ms-marco-MiniLM-L-6-v2`"
        )

    # --- HERO BANNER & KPI METRICS ---
    g_stats = citation_graph.get_stats()
    ingested_papers = get_ingested_papers_list(citation_graph, vector_store)

    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-title">🎓 ScholarRAG — Trợ lý Tổng hợp & Phân tích Bài báo Khoa học</div>
            <p class="hero-subtitle">
                Phân tích PDF học thuật theo cấu trúc đề mục (Section-Aware), tìm kiếm kết hợp (Hybrid Qdrant + BM25 + Cross-Encoder Reranking),
                khai phá đồ thị trích dẫn (Citation Graph) và tổng hợp đối sánh có kiểm chứng chống ảo giác.
            </p>
            <div class="badge-row">
                <span class="tech-badge">📄 PyMuPDF4LLM + RapidOCR</span>
                <span class="tech-badge">🔍 Hybrid RRF (Qdrant + BM25)</span>
                <span class="tech-badge">🎯 ONNX Cross-Encoder Reranker</span>
                <span class="tech-badge">🕸️ NetworkX Citation Graph</span>
                <span class="tech-badge">🛡️ Citation Grounding Guard</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📚 Bài báo trong Thư viện", g_stats["ingested_papers"])
    m2.metric("🧩 Phân đoạn (Section Chunks)", len(vector_store.chunks_by_id))
    m3.metric("🕸️ Tổng nút Đồ thị Trích dẫn", g_stats["total_nodes"])
    m4.metric("🔗 Liên kết Trích dẫn (Edges)", g_stats["total_citation_edges"])

    # --- MAIN WORKSPACE TABS ---
    tab_research, tab_library, tab_eval = st.tabs(
        [
            "💬 Hỏi đáp & Tổng hợp Nghiên cứu",
            f"📚 Thư viện Bài báo & Đồ thị ({g_stats['ingested_papers']})",
            "📊 Đánh giá Hệ thống (Ablation Benchmark)",
        ]
    )

    # ================= TAB 1: RESEARCH & SYNTHESIS =================
    with tab_research:
        if not ingested_papers:
            st.info(
                "👋 Thư viện hiện chưa có bài báo nào. Hãy dùng thanh công cụ bên trái (**📥 1. Thêm bài báo khoa học**) "
                "để tìm bài báo từ ArXiv hoặc tải file PDF từ máy tính lên!"
            )
        else:
            st.markdown("##### 💡 Gợi ý câu hỏi nhanh từ thư viện hiện tại của bạn")
            suggestion_cols = st.columns(3)
            suggestions = []
            first_title = ingested_papers[0]["title"]
            short_t1 = first_title[:42] + ("..." if len(first_title) > 42 else "")
            suggestions.append(
                (
                    f"📌 Đóng góp chính: {short_t1}",
                    f"What are the main methodology, architectural innovations, and key experimental findings of '{first_title}'?",
                )
            )
            if len(ingested_papers) >= 2:
                second_title = ingested_papers[1]["title"]
                short_t2 = second_title[:38] + ("..." if len(second_title) > 38 else "")
                suggestions.append(
                    (
                        f"⚖️ So sánh 2 bài: {short_t1[:20]}... vs {short_t2[:20]}...",
                        f"Compare the methodology, key differences, and experimental results between '{first_title}' and '{second_title}'.",
                    )
                )
            else:
                suggestions.append(
                    (
                        "🔬 Phân tích Thực nghiệm & Benchmark",
                        f"What datasets, evaluation metrics, and ablation studies are reported in '{first_title}'?",
                    )
                )
            suggestions.append(
                (
                    "⚠️ Hạn chế & Hướng phát triển",
                    "What are the main limitations, bottlenecks, or future work directions discussed across the indexed papers?",
                )
            )

            for idx, (label, full_q) in enumerate(suggestions):
                if suggestion_cols[idx].button(label, key=f"sug_{idx}", use_container_width=True):
                    st.session_state.active_question = full_q

            with st.form("research_query_form", clear_on_submit=False):
                q_col, btn_col = st.columns([5, 1])
                user_question = q_col.text_input(
                    "Đặt câu hỏi nghiên cứu hoặc yêu cầu so sánh giữa các bài báo:",
                    value=st.session_state.active_question,
                    placeholder="Nhập câu hỏi bằng tiếng Anh hoặc tiếng Việt (VD: Compare method A and method B...)",
                )
                submitted = btn_col.form_submit_button(
                    "🔍 Tổng hợp",
                    type="primary",
                    use_container_width=True,
                )

            if submitted and user_question.strip():
                retriever = HybridGraphRetriever(
                    vector_store=vector_store,
                    citation_graph=citation_graph,
                    search_mode=search_mode,
                )
                agent = LiteratureReviewAgent(retriever=retriever, llm_client=llm_client)

                with st.spinner("Đang phân rã truy vấn, tìm kiếm Hybrid + Cross-Encoder và tổng hợp trích dẫn..."):
                    response = agent.run(user_question.strip())
                    st.session_state.qa_history.insert(0, response)

            if st.session_state.qa_history:
                top_bar_left, top_bar_right = st.columns([4, 1])
                top_bar_left.markdown(f"#### 📑 Kết quả Tổng hợp ({len(st.session_state.qa_history)} phiên hỏi đáp)")
                if top_bar_right.button("🧹 Xóa lịch sử trả lời", use_container_width=True):
                    st.session_state.qa_history = []
                    st.rerun()

                for item_idx, resp in enumerate(st.session_state.qa_history):
                    with st.container(border=True):
                        head_col, badge_col, dl_col = st.columns([3.5, 1.5, 1])
                        head_col.markdown(f"##### ❓ {resp.question}")
                        if resp.is_grounded:
                            badge_col.success("✅ Trích dẫn đã kiểm chứng")
                        else:
                            badge_col.warning("⚠️ Kiểm tra nguồn bên dưới")

                        md_export = (
                            f"# ScholarRAG Literature Review\n\n"
                            f"**Question:** {resp.question}\n\n"
                            f"## Synthesized Answer\n{resp.answer}\n\n"
                            f"## Retrieved Sources\n"
                            + "\n".join(
                                f"- {p.citation_tag} ({p.chunk.paper_title}): Rerank={p.rerank_score:.4f}"
                                for p in resp.citations
                            )
                        )
                        dl_col.download_button(
                            "⬇️ Tải .md",
                            data=md_export,
                            file_name=f"scholarrag_review_{item_idx + 1}.md",
                            mime="text/markdown",
                            key=f"dl_{item_idx}",
                            use_container_width=True,
                        )

                        st.markdown(resp.answer)

                        detail_tab1, detail_tab2, detail_tab3 = st.tabs(
                            [
                                f"📄 Nguồn trích dẫn ({len(resp.citations)} phân đoạn)",
                                f"🧠 Phân rã Truy vấn ({len(resp.sub_queries)} sub-queries)",
                                f"🕸️ Mở rộng Đồ thị Trích dẫn ({len(resp.related_papers_from_graph)})",
                            ]
                        )

                        with detail_tab1:
                            for p_idx, p in enumerate(resp.citations, start=1):
                                s_col1, s_col2 = st.columns([3.5, 2.5])
                                s_col1.markdown(
                                    f"**#{p_idx} {p.citation_tag}**  \n*{p.chunk.paper_title}*"
                                )
                                s_col2.caption(
                                    f"🎯 **Rerank:** `{p.rerank_score:.4f}` | "
                                    f"🧭 **Dense:** `{p.dense_score:.4f}` | "
                                    f"🔤 **BM25:** `{p.sparse_score:.4f}`"
                                )
                                with st.expander("Xem toàn văn đoạn trích (Markdown)", expanded=(p_idx == 1)):
                                    st.markdown(p.chunk.content)

                        with detail_tab2:
                            st.caption("Agent tự động tách câu hỏi gốc thành các truy vấn con để bao phủ nhiều bài báo:")
                            for sq_i, sq in enumerate(resp.sub_queries, start=1):
                                st.markdown(f"{sq_i}. `{sq}`")

                        with detail_tab3:
                            if not resp.related_papers_from_graph:
                                st.caption("Không có liên kết trích dẫn mở rộng cho truy vấn này.")
                            else:
                                st.caption("Các bài báo cùng trích dẫn (co-citation) hoặc tài liệu nền tảng được phát hiện qua đồ thị:")
                                for rel in resp.related_papers_from_graph:
                                    st.markdown(f"- {rel}")

    # ================= TAB 2: PAPER LIBRARY & GRAPH =================
    with tab_library:
        lib_col_left, lib_col_right = st.columns([1.25, 1])

        with lib_col_left:
            st.markdown("#### 📚 Danh sách Bài báo đã nạp")
            filter_kw = st.text_input(
                "🔍 Lọc bài báo theo tên, tác giả hoặc mã ID:",
                placeholder="Gõ từ khóa để lọc...",
            )

            filtered_papers = [
                p
                for p in ingested_papers
                if not filter_kw.strip()
                or filter_kw.lower() in p["title"].lower()
                or filter_kw.lower() in p["paper_id"].lower()
                or any(filter_kw.lower() in a.lower() for a in p["authors"])
            ]

            if not filtered_papers:
                st.info("Không có bài báo nào khớp với bộ lọc.")
            else:
                for p in filtered_papers:
                    pid = p["paper_id"]
                    with st.container(border=True):
                        c_title, c_del = st.columns([5, 1])
                        c_title.markdown(f"##### 📄 [{pid}] {p['title']}")
                        if c_del.button("🗑️ Xóa", key=f"del_{pid}", use_container_width=True):
                            removed = pipeline.delete_paper(pid)
                            st.toast(f"Đã xóa {pid} ({removed} phân đoạn).")
                            st.rerun()

                        authors_str = ", ".join(p["authors"][:6]) + (" et al." if len(p["authors"]) > 6 else "")
                        st.caption(
                            f"👤 **Tác giả:** {authors_str or 'N/A'}  \n"
                            f"📅 **Ngày công bố:** `{p['published_date']}` | "
                            f"📈 **Trích dẫn (OpenAlex):** `{p['citation_count']}` | "
                            f"🧩 **Số chunks:** `{p['chunk_count']}` | "
                            f"🔗 **Tài liệu tham khảo:** `{p['out_refs']}`"
                        )

                        if re.match(r"^\d{4}\.\d{4,5}$", pid):
                            st.markdown(
                                f"🔗 [Trang ArXiv Abstract](https://arxiv.org/abs/{pid}) &nbsp;•&nbsp; "
                                f"📥 [PDF Gốc trên ArXiv](https://arxiv.org/pdf/{pid}.pdf)"
                            )

                        with st.expander(f"Xem cấu trúc {len(p['sections'])} đề mục (Sections) đã bóc tách"):
                            pills_html = "".join(
                                f'<span class="section-pill">{sec}</span>' for sec in p["sections"]
                            )
                            st.markdown(pills_html, unsafe_allow_html=True)

        with lib_col_right:
            st.markdown("#### 🕸️ Sơ đồ Mạng lưới Trích dẫn (Citation Graph)")
            st.caption(
                "Các ô **màu xanh dương** là bài báo trong thư viện; các hình elip **màu vàng cam** là tài liệu nền tảng được nhiều bài cùng trích dẫn (Co-cited References)."
            )
            if g_stats["ingested_papers"] == 0:
                st.info("Nạp ít nhất 1 bài báo để trực quan hóa đồ thị trích dẫn.")
            else:
                max_ext_nodes = st.slider(
                    "Số nút tham khảo ngoại vi hiển thị tối đa",
                    min_value=5,
                    max_value=50,
                    value=20,
                )
                dot_str = build_citation_dot_graph(citation_graph, max_external=max_ext_nodes)
                st.graphviz_chart(dot_str, use_container_width=True)

    # ================= TAB 3: EVALUATION & ABLATION =================
    with tab_eval:
        st.markdown("#### 📊 Thực nghiệm Đối sánh (Ablation Study): Dense vs. BM25 vs. Hybrid + Rerank")
        dynamic_samples = build_dynamic_benchmark(vector_store)
        st.write(
            f"Hệ thống tự động sinh **{len(dynamic_samples)} câu hỏi kiểm thử (Benchmark)** dựa trên chính các bài báo đang có trong thư viện của bạn "
            "để đo lường khách quan 4 chỉ số RAG:"
        )
        e_col1, e_col2, e_col3, e_col4 = st.columns(4)
        e_col1.info("**Context Precision**\n\nTỷ lệ đoạn văn lấy ra thuộc đúng bài báo chuẩn (Ground-truth).")
        e_col2.info("**Context Recall**\n\nĐộ phủ bài báo chuẩn và các thuật ngữ kỹ thuật cốt lõi.")
        e_col3.info("**Citation Faithfulness**\n\nTỷ lệ trích dẫn `[id: mục]` trong câu trả lời khớp 100% với nguồn.")
        e_col4.info("**Answer Relevance**\n\nMức độ bao phủ các khái niệm mục tiêu trong câu trả lời tổng hợp.")

        with st.expander(f"📋 Xem danh sách {len(dynamic_samples)} câu hỏi Benchmark tự động", expanded=False):
            for idx, s in enumerate(dynamic_samples, start=1):
                st.markdown(
                    f"**{idx}. {s.question}**  \n"
                    f"- *Bài báo kỳ vọng:* `{', '.join(s.expected_paper_ids)}` | "
                    f"*Từ khóa mục tiêu:* `{', '.join(s.expected_keywords)}`"
                )

        if st.button("▶️ Chạy Thực nghiệm Đối sánh (Run Ablation Study)", type="primary"):
            evaluator = RAGEvaluator()
            with st.spinner("Đang chạy đánh giá trên cả 3 chế độ: Dense-Only, Sparse BM25, và Hybrid + CrossEncoder..."):
                ablation = evaluator.run_ablation_study(
                    vector_store=vector_store,
                    citation_graph=citation_graph,
                    samples=dynamic_samples,
                )

            rows = []
            mode_labels = {
                "dense": "1️⃣ Dense Only (Qdrant BGE-Small)",
                "sparse": "2️⃣ Sparse Only (BM25Okapi)",
                "hybrid": "3️⃣ Hybrid (Qdrant + BM25 + CrossEncoder)",
            }
            for mode_name, metrics in ablation.items():
                rows.append(
                    {
                        "Phương pháp Truy vấn": mode_labels.get(mode_name, mode_name.upper()),
                        "Context Precision": f"{metrics['mean_context_precision']:.3f}",
                        "Context Recall": f"{metrics['mean_context_recall']:.3f}",
                        "Citation Faithfulness": f"{metrics['mean_citation_faithfulness']:.3f}",
                        "Answer Relevance": f"{metrics['mean_answer_relevance']:.3f}",
                    }
                )
            st.markdown("##### 🏆 Bảng Kết quả Ablation Study")
            st.table(rows)

            for mode_name, metrics in ablation.items():
                with st.expander(f"Chi tiết điểm số từng câu hỏi — {mode_labels.get(mode_name, mode_name)}"):
                    st.dataframe(metrics["details"], use_container_width=True)


if __name__ == "__main__":
    main()
