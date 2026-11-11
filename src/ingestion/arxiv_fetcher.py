from datetime import date
import re
import time
from pathlib import Path
from typing import Dict, List, Optional
import httpx

from src.config import settings
from src.models.schemas import PaperMetadata


class ArxivFetcher:
    """
    Fetches research paper metadata and PDFs from ArXiv and OpenAlex.
    Includes automatic multi-source fallback: if export.arxiv.org rate-limits (HTTP 429/503),
    transparently falls back to OpenAlex API to resolve ArXiv papers, abstracts, and PDFs.
    """

    OPENALEX_API_URL = "https://api.openalex.org/works"
    ARXIV_ID_REGEX = re.compile(
        r"^(?:https?://(?:export\.)?arxiv\.org/(?:abs|pdf)/)?((?:\d{4}\.\d{4,5})|(?:[a-zA-Z\-]+/\d{7}))(?:v\d+)?(?:\.pdf)?$",
        re.IGNORECASE,
    )
    USER_AGENT = "MiniNotebook/0.1 (mailto:research-assistant@example.org)"

    def __init__(self, download_dir: Optional[Path] = None):
        self.download_dir = download_dir or settings.raw_pdf_dir
        self.download_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def normalize_arxiv_id(raw_id: str) -> str:
        """Strip URL prefix and version suffix (e.g., 'https://arxiv.org/abs/2305.14314v2' -> '2305.14314', 'hep-th/9901001v1' -> 'hep-th/9901001')."""
        cleaned = raw_id.strip()
        cleaned = re.sub(r"^https?://(?:export\.)?arxiv\.org/(?:abs|pdf)/", "", cleaned, flags=re.IGNORECASE)
        if cleaned.lower().endswith(".pdf"):
            cleaned = cleaned[:-4]
        cleaned = re.sub(r"v\d+$", "", cleaned)
        return cleaned.strip()

    @classmethod
    def extract_arxiv_id_from_work(cls, work: Dict) -> Optional[str]:
        """Extract normalized ArXiv ID from an OpenAlex work record if available."""
        doi = (work.get("doi") or "").strip()
        if "10.48550/arxiv." in doi.lower():
            raw_id = doi.lower().split("10.48550/arxiv.")[-1]
            return cls.normalize_arxiv_id(raw_id)

        ids_dict = work.get("ids") or {}
        for val in ids_dict.values():
            if isinstance(val, str) and "arxiv.org" in val:
                return cls.normalize_arxiv_id(val)

        for loc in work.get("locations") or []:
            landing = (loc.get("landing_page_url") or "")
            pdf_u = (loc.get("pdf_url") or "")
            for url_candidate in (landing, pdf_u):
                if "arxiv.org/" in url_candidate:
                    return cls.normalize_arxiv_id(url_candidate)
        return None

    @staticmethod
    def reconstruct_openalex_abstract(inverted_index: Optional[Dict[str, List[int]]]) -> str:
        """Reconstruct plain-text abstract from OpenAlex abstract_inverted_index."""
        if not inverted_index:
            return ""
        pos_to_word: Dict[int, str] = {}
        for word, positions in inverted_index.items():
            for pos in positions:
                pos_to_word[pos] = word
        if not pos_to_word:
            return ""
        return " ".join(pos_to_word[idx] for idx in sorted(pos_to_word.keys()))

    def search_papers(self, query: str, max_results: int = 5) -> List[PaperMetadata]:
        """
        Search ArXiv for papers matching the query.
        1. Sets page_size = max_results (instead of default 100) to avoid ArXiv HTTP 429 rate-limiting.
        2. Automatically falls back to OpenAlex API if export.arxiv.org returns HTTP 429 or 503.
        """
        import arxiv

        cleaned_query = query.strip()
        id_match = self.ARXIV_ID_REGEX.match(cleaned_query)

        # Keep page_size small (= max_results) so ArXiv API does not fetch 100 entries per call
        client = arxiv.Client(
            page_size=max(min(max_results, 10), 1),
            delay_seconds=3.5,
            num_retries=2,
        )

        if id_match:
            search = arxiv.Search(id_list=[id_match.group(1)], max_results=1)
        else:
            search = arxiv.Search(
                query=cleaned_query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance,
            )

        papers: List[PaperMetadata] = []
        try:
            for result in client.results(search):
                paper_id = self.normalize_arxiv_id(result.entry_id)
                papers.append(
                    PaperMetadata(
                        paper_id=paper_id,
                        title=result.title.replace("\n", " ").strip(),
                        authors=[a.name for a in result.authors],
                        published_date=result.published.date() if result.published else None,
                        abstract=result.summary.replace("\n", " ").strip(),
                        categories=list(result.categories),
                        pdf_url=result.pdf_url,
                    )
                )
            if papers:
                return papers
        except Exception:
            # ArXiv API rate-limited (HTTP 429 / 503) or temporarily unavailable -> fallback to OpenAlex
            pass

        return self.search_papers_openalex_fallback(query=cleaned_query, max_results=max_results)

    def search_papers_openalex_fallback(self, query: str, max_results: int = 5) -> List[PaperMetadata]:
        """
        Fallback search via OpenAlex API when export.arxiv.org returns HTTP 429 / 503.
        Fetches works indexed from ArXiv (`locations.source.id:S4306400194`) or matching ArXiv DOIs.
        """
        params = {
            "search": query,
            "filter": "Indexed_in:arxiv|locations.source.id:S4306400194",
            "per-page": max(max_results * 3, 10),
        }
        headers = {"User-Agent": self.USER_AGENT}
        papers: List[PaperMetadata] = []

        try:
            with httpx.Client(timeout=20.0, headers=headers) as client:
                resp = client.get(self.OPENALEX_API_URL, params=params)
                if resp.status_code != 200:
                    # Retry without strict filter in case filter syntax varies
                    resp = client.get(
                        self.OPENALEX_API_URL,
                        params={"search": f"{query} arxiv", "per-page": max(max_results * 4, 15)},
                    )
                resp.raise_for_status()
                results = resp.json().get("results", [])

                for work in results:
                    arxiv_id = self.extract_arxiv_id_from_work(work)
                    if not arxiv_id:
                        continue

                    pub_date_str = work.get("publication_date")
                    pub_date = None
                    if pub_date_str:
                        try:
                            pub_date = date.fromisoformat(pub_date_str)
                        except ValueError:
                            pub_date = None

                    authors = [
                        (auth.get("author") or {}).get("display_name", "")
                        for auth in (work.get("authorships") or [])
                        if (auth.get("author") or {}).get("display_name")
                    ]
                    abstract = self.reconstruct_openalex_abstract(work.get("abstract_inverted_index"))
                    referenced_works = work.get("referenced_works") or []

                    papers.append(
                        PaperMetadata(
                            paper_id=arxiv_id,
                            title=(work.get("title") or f"Paper {arxiv_id}").strip(),
                            authors=authors,
                            published_date=pub_date,
                            abstract=abstract,
                            categories=["arXiv"],
                            pdf_url=f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                            citation_count=work.get("cited_by_count", 0),
                            references=[w.split("/")[-1] for w in referenced_works[:50]],
                        )
                    )
                    if len(papers) >= max_results:
                        break
        except httpx.HTTPError:
            pass

        return papers

    def download_pdf(self, paper: PaperMetadata) -> Path:
        """Download the PDF for a paper with retry and User-Agent header if not already cached locally."""
        safe_filename = paper.paper_id.replace("/", "_")
        target_path = self.download_dir / f"{safe_filename}.pdf"
        if target_path.exists() and target_path.stat().st_size > 0:
            paper.local_pdf_path = str(target_path)
            return target_path

        candidate_urls = [
            paper.pdf_url or f"https://arxiv.org/pdf/{paper.paper_id}.pdf",
            f"https://export.arxiv.org/pdf/{paper.paper_id}.pdf",
        ]
        headers = {"User-Agent": self.USER_AGENT}

        last_err = None
        for url in candidate_urls:
            for attempt in range(2):
                try:
                    with httpx.Client(follow_redirects=True, timeout=60.0, headers=headers) as client:
                        response = client.get(url)
                        if response.status_code == 429:
                            time.sleep(3.0 * (attempt + 1))
                            continue
                        response.raise_for_status()
                        target_path.write_bytes(response.content)
                        paper.local_pdf_path = str(target_path)
                        return target_path
                except Exception as exc:
                    last_err = exc
                    time.sleep(1.5)

        raise RuntimeError(f"Failed to download PDF for {paper.paper_id}: {last_err}")

    def enrich_citations_openalex(self, paper: PaperMetadata) -> PaperMetadata:
        """Enrich paper metadata with citation count and referenced works from OpenAlex."""
        if paper.references and paper.citation_count > 0:
            return paper

        url = f"{self.OPENALEX_API_URL}/https://doi.org/10.48550/arXiv.{paper.paper_id}"
        headers = {"User-Agent": self.USER_AGENT}
        try:
            with httpx.Client(timeout=15.0, headers=headers) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    paper.citation_count = data.get("cited_by_count", 0)
                    referenced_works = data.get("referenced_works", [])
                    paper.references = [w.split("/")[-1] for w in referenced_works[:50]]
        except httpx.HTTPError:
            pass
        return paper
