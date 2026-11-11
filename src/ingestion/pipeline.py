from pathlib import Path
from typing import Dict, List, Optional

from src.indexing.citation_graph import CitationGraphStore
from src.indexing.vector_store import HybridVectorStore
from src.ingestion.arxiv_fetcher import ArxivFetcher
from src.ingestion.chunker import SectionAwareChunker
from src.ingestion.pdf_parser import AcademicPDFParser
from src.models.schemas import PaperMetadata


class IngestionPipeline:
    """
    End-to-end Ingestion & Indexing Pipeline:
    1. Search ArXiv & enrich citation metadata via OpenAlex (or ingest local PDF)
    2. Download PDF & parse multi-column layout into page-level Markdown
    3. Split into section-aware chunks (skipping noisy References)
    4. Index chunks into HybridVectorStore (Qdrant + BM25) and update CitationGraphStore
    """

    def __init__(
        self,
        vector_store: HybridVectorStore,
        citation_graph: CitationGraphStore,
        fetcher: Optional[ArxivFetcher] = None,
        parser: Optional[AcademicPDFParser] = None,
        chunker: Optional[SectionAwareChunker] = None,
    ):
        self.vector_store = vector_store
        self.citation_graph = citation_graph
        self.fetcher = fetcher or ArxivFetcher()
        self.parser = parser or AcademicPDFParser()
        self.chunker = chunker or SectionAwareChunker()

    def ingest_topic(self, query: str, max_papers: int = 3) -> Dict[str, object]:
        """Search ArXiv for a topic, download, parse, chunk, and index all papers."""
        papers = self.fetcher.search_papers(query=query, max_results=max_papers)
        total_chunks = 0
        success_count = 0
        failed: List[Dict[str, str]] = []

        for paper in papers:
            try:
                total_chunks += self.ingest_single_paper(paper)
                success_count += 1
            except Exception as e:
                failed.append({"paper_id": paper.paper_id, "error": str(e)})

        if success_count > 0:
            self.citation_graph.resolve_reference_titles(max_nodes=40)
            self.citation_graph.save()

        return {
            "papers_ingested": success_count,
            "chunks_indexed": total_chunks,
            "failed": failed,
        }

    def ingest_single_paper(self, paper: PaperMetadata, force: bool = False) -> int:
        """Download, enrich, parse, chunk, and index a single paper (skipping or replacing existing chunks)."""
        if not force and self.citation_graph.graph.has_node(paper.paper_id):
            if self.citation_graph.graph.nodes[paper.paper_id].get("ingested", False):
                existing = sum(1 for c in self.vector_store.chunks_by_id.values() if c.paper_id == paper.paper_id)
                if existing > 0:
                    return 0

        # Clear old chunks if re-indexing to avoid duplicates (COR-05)
        self.vector_store.delete_paper_chunks(paper.paper_id)

        paper = self.fetcher.enrich_citations_openalex(paper)
        pdf_path = self.fetcher.download_pdf(paper)
        pages_data = self.parser.parse_pdf_to_pages(pdf_path=pdf_path, paper_id=paper.paper_id)
        chunks = self.chunker.chunk_paper(paper=paper, pages_data=pages_data)

        indexed_count = self.vector_store.index_chunks(chunks)
        self.citation_graph.add_paper(paper)
        return indexed_count

    def ingest_local_pdf(self, pdf_path: Path, title: Optional[str] = None) -> Dict[str, object]:
        """Parse, chunk, and index a user-uploaded local PDF file."""
        paper_id = pdf_path.stem.replace(" ", "_")
        # Clear old chunks if this paper was previously uploaded (COR-05)
        self.vector_store.delete_paper_chunks(paper_id)

        pages_data = self.parser.parse_pdf_to_pages(pdf_path=pdf_path, paper_id=paper_id)

        inferred_title = title or pdf_path.stem.replace("_", " ").replace("-", " ")
        if not title and pages_data:
            first_lines = [
                line.lstrip("#* ").strip()
                for line in pages_data[0]["text"].splitlines()
                if line.strip() and not line.strip().startswith("<!--")
            ]
            if first_lines:
                inferred_title = first_lines[0][:140]

        paper = PaperMetadata(
            paper_id=paper_id,
            title=inferred_title,
            authors=["Local Upload"],
            local_pdf_path=str(pdf_path),
            categories=["local-pdf"],
        )
        chunks = self.chunker.chunk_paper(paper=paper, pages_data=pages_data)
        indexed_count = self.vector_store.index_chunks(chunks)
        self.citation_graph.add_paper(paper)
        self.citation_graph.save()
        return {
            "paper_id": paper_id,
            "title": inferred_title,
            "chunks_indexed": indexed_count,
        }

    def delete_paper(self, paper_id: str) -> int:
        """Remove a paper from Vector Store, Citation Graph, and delete cached raw/parsed files."""
        removed_chunks = self.vector_store.delete_paper_chunks(paper_id)
        self.citation_graph.remove_paper(paper_id)

        # Clean up cached files from disk (COR-09)
        safe_id = paper_id.replace("/", "_")
        for pdf_file in settings.raw_pdf_dir.glob(f"{safe_id}.pdf"):
            try:
                pdf_file.unlink(missing_ok=True)
            except Exception:
                pass
        for md_file in settings.parsed_md_dir.glob(f"{safe_id}*.md"):
            try:
                md_file.unlink(missing_ok=True)
            except Exception:
                pass
        return removed_chunks
