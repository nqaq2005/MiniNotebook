from pathlib import Path
from typing import Dict, List, Optional

from src.config import settings


class AcademicPDFParser:
    """Parses multi-column scientific PDFs into structured Markdown preserving headings and tables."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or settings.parsed_md_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def parse_pdf_to_pages(self, pdf_path: Path, paper_id: str) -> List[Dict]:
        """
        Convert a PDF into page-by-page structured Markdown chunks using PyMuPDF4LLM.
        Returns a list of dicts: [{'page': int, 'text': str}, ...]
        """
        import pymupdf4llm

        page_chunks = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)
        pages_data: List[Dict] = []
        full_md_parts: List[str] = []

        for idx, page in enumerate(page_chunks):
            page_num = page.get("metadata", {}).get("page", idx + 1)
            text = page.get("text", "").strip()
            pages_data.append({"page": page_num, "text": text})
            full_md_parts.append(f"<!-- PAGE {page_num} -->\n{text}")

        md_output_path = self.output_dir / f"{paper_id}.md"
        md_output_path.write_text("\n\n".join(full_md_parts), encoding="utf-8")
        return pages_data
