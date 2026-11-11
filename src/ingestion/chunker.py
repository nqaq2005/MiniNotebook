import re
from typing import Dict, List

from src.config import settings
from src.models.schemas import PaperMetadata, SectionChunk


class SectionAwareChunker:
    """
    Splits parsed academic Markdown into logical section chunks
    (Abstract, Introduction, Methodology, Experiments, Conclusion, etc.)
    while stripping out noisy Bibliography/References sections if desired.
    """

    HEADING_PATTERN = re.compile(
        r"^(#{1,4}\s+.+|\*\*(?:\d+(?:\.\d+)*\s+)?[A-Z][A-Za-z0-9\s\-:,]{2,60}\*\*)$",
        re.MULTILINE,
    )
    SKIP_SECTIONS = {"references", "bibliography", "acknowledgments", "acknowledgements"}

    def __init__(
        self,
        max_chars: int = settings.chunk_max_chars,
        overlap_chars: int = settings.chunk_overlap_chars,
        skip_references: bool = True,
    ):
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars
        self.skip_references = skip_references

    @staticmethod
    def _clean_heading(raw_heading: str) -> str:
        cleaned = raw_heading.strip().lstrip("#").strip()
        cleaned = cleaned.strip("*").strip()
        return cleaned

    def _should_skip_section(self, section_title: str) -> bool:
        if not self.skip_references:
            return False
        normalized = re.sub(r"^\d+(?:\.\d+)*\s*", "", section_title.lower()).strip().rstrip(":")
        return normalized in self.SKIP_SECTIONS or any(
            normalized.startswith(s) for s in self.SKIP_SECTIONS
        )

    def chunk_paper(
        self,
        paper: PaperMetadata,
        pages_data: List[Dict],
    ) -> List[SectionChunk]:
        """
        Chunk a paper into section-aware segments with page number tracking.
        Always includes the Abstract as the first chunk if present.
        """
        chunks: List[SectionChunk] = []

        if paper.abstract:
            chunks.append(
                SectionChunk(
                    chunk_id=f"{paper.paper_id}_abstract_0",
                    paper_id=paper.paper_id,
                    paper_title=paper.title,
                    section_title="Abstract",
                    page_numbers=[1],
                    content=paper.abstract,
                    token_estimate=len(paper.abstract) // 4,
                )
            )

        sections = self._extract_sections_from_pages(pages_data)

        for sec_idx, sec in enumerate(sections):
            sec_title = sec["section_title"]
            if self._should_skip_section(sec_title):
                continue
            if paper.abstract and sec_title.strip().lower() == "abstract":
                continue

            sub_texts = self._split_text_with_overlap(sec["content"])
            for sub_idx, text in enumerate(sub_texts):
                if not text.strip():
                    continue
                chunks.append(
                    SectionChunk(
                        chunk_id=f"{paper.paper_id}_sec{sec_idx}_{sub_idx}",
                        paper_id=paper.paper_id,
                        paper_title=paper.title,
                        section_title=sec_title,
                        page_numbers=sorted(list(sec["pages"])),
                        content=text.strip(),
                        token_estimate=len(text) // 4,
                    )
                )

        return chunks

    def _extract_sections_from_pages(self, pages_data: List[Dict]) -> List[Dict]:
        """Group page text by detected academic section headings."""
        sections: List[Dict] = []
        current_section = {
            "section_title": "Introduction / Overview",
            "content": "",
            "pages": set(),
        }

        for page_item in pages_data:
            page_num = page_item["page"]
            lines = page_item["text"].splitlines()

            for line in lines:
                stripped = line.strip()
                is_caption = stripped.lower().startswith((
                    "**figure", "**fig.", "**fig ", "**table", "**tab.", "**tab ",
                    "**note", "**algorithm", "**definition", "**theorem", "**lemma"
                ))
                if not is_caption and self.HEADING_PATTERN.match(stripped):
                    if current_section["content"].strip():
                        sections.append(current_section)
                    current_section = {
                        "section_title": self._clean_heading(stripped),
                        "content": "",
                        "pages": {page_num},
                    }
                else:
                    current_section["content"] += line + "\n"
                    current_section["pages"].add(page_num)

        if current_section["content"].strip():
            sections.append(current_section)

        return sections

    def _split_text_with_overlap(self, text: str) -> List[str]:
        """Split long section text by paragraphs while respecting max_chars and overlap."""
        text = text.strip()
        if len(text) <= self.max_chars:
            return [text]

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        results: List[str] = []
        current = ""

        for para in paragraphs:
            if len(current) + len(para) + 2 <= self.max_chars:
                current = f"{current}\n\n{para}".strip()
            else:
                if current:
                    results.append(current)
                    overlap = current[-self.overlap_chars :] if self.overlap_chars > 0 else ""
                    current = f"{overlap}\n\n{para}".strip()
                else:
                    # Single paragraph exceeds max_chars
                    for i in range(0, len(para), self.max_chars - self.overlap_chars):
                        results.append(para[i : i + self.max_chars])
                    current = ""

        if current:
            results.append(current)

        return results
