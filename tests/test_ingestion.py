from src.ingestion.arxiv_fetcher import ArxivFetcher
from src.ingestion.chunker import SectionAwareChunker
from src.models.schemas import PaperMetadata


def test_normalize_arxiv_id():
    assert ArxivFetcher.normalize_arxiv_id("https://arxiv.org/abs/2305.14314v2") == "2305.14314"
    assert ArxivFetcher.normalize_arxiv_id("2401.00001v1") == "2401.00001"
    assert ArxivFetcher.normalize_arxiv_id("https://arxiv.org/pdf/2305.14314v1.pdf") == "2305.14314"


def test_openalex_fallback_helpers():
    mock_work = {
        "doi": "https://doi.org/10.48550/arXiv.2305.14314",
        "abstract_inverted_index": {"We": [0], "present": [1], "QLoRA.": [2]},
    }
    assert ArxivFetcher.extract_arxiv_id_from_work(mock_work) == "2305.14314"
    assert ArxivFetcher.reconstruct_openalex_abstract(mock_work["abstract_inverted_index"]) == "We present QLoRA."


def test_section_aware_chunker_splits_sections_and_skips_references():
    paper = PaperMetadata(
        paper_id="2305.14314",
        title="QLoRA: Efficient Finetuning of Quantized LLMs",
        authors=["Tim Dettmers"],
        abstract="We present QLoRA, an efficient finetuning approach.",
    )
    pages_data = [
        {
            "page": 1,
            "text": "# 1 Introduction\nFinetuning large language models is expensive.\n\n## 2 Methodology\nWe introduce 4-bit NormalFloat quantization.",
        },
        {
            "page": 2,
            "text": "# 3 Experiments\nWe evaluate on MMLU benchmark.\n\n# References\n[1] Hu et al., LoRA 2021.",
        },
    ]

    chunker = SectionAwareChunker(max_chars=500, overlap_chars=50, skip_references=True)
    chunks = chunker.chunk_paper(paper, pages_data)

    section_titles = [c.section_title for c in chunks]
    assert "Abstract" in section_titles
    assert "1 Introduction" in section_titles
    assert "2 Methodology" in section_titles
    assert "3 Experiments" in section_titles
    assert "References" not in section_titles
