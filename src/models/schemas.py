from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field


class PaperMetadata(BaseModel):
    """Core metadata for a scientific research paper."""

    paper_id: str = Field(..., description="Unique identifier (e.g., ArXiv ID like '2305.14314')")
    title: str = Field(..., description="Full title of the paper")
    authors: List[str] = Field(default_factory=list, description="List of author names")
    published_date: Optional[date] = Field(None, description="Publication date")
    abstract: str = Field("", description="Paper abstract")
    categories: List[str] = Field(default_factory=list, description="ArXiv/subject categories")
    pdf_url: Optional[str] = Field(None, description="Direct URL to the PDF")
    local_pdf_path: Optional[str] = Field(None, description="Local path to downloaded PDF")
    references: List[str] = Field(
        default_factory=list,
        description="List of referenced paper IDs or titles for the citation graph",
    )
    citation_count: int = Field(0, description="Number of incoming citations (if available)")


class SectionChunk(BaseModel):
    """A structured, section-aware text chunk extracted from a paper."""

    chunk_id: str = Field(..., description="Unique chunk identifier (e.g. '2305.14314_sec2_0')")
    paper_id: str = Field(..., description="Parent paper identifier")
    paper_title: str = Field(..., description="Parent paper title")
    section_title: str = Field(..., description="Section heading (e.g., '3. Methodology')")
    page_numbers: List[int] = Field(default_factory=list, description="Pages covered by this chunk")
    content: str = Field(..., description="Markdown text content of the chunk")
    token_estimate: int = Field(0, description="Approximate token count")


class RetrievedPassage(BaseModel):
    """A retrieved chunk along with relevance scores and citation info."""

    chunk: SectionChunk
    dense_score: float = 0.0
    sparse_score: float = 0.0
    rerank_score: float = 0.0

    @property
    def citation_tag(self) -> str:
        pages = f", p.{','.join(map(str, self.chunk.page_numbers))}" if self.chunk.page_numbers else ""
        return f"[{self.chunk.paper_id}: {self.chunk.section_title}{pages}]"


class SynthesisResponse(BaseModel):
    """Final synthesized answer returned by the Agentic RAG workflow."""

    question: str
    sub_queries: List[str] = Field(default_factory=list)
    answer: str
    citations: List[RetrievedPassage] = Field(default_factory=list)
    related_papers_from_graph: List[str] = Field(default_factory=list)
    is_grounded: bool = True
