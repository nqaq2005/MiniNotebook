import json
from pathlib import Path
from typing import Dict, List, Optional, Set
import httpx
import networkx as nx

from src.config import settings
from src.models.schemas import PaperMetadata


class CitationGraphStore:
    """
    Manages a directed citation graph using NetworkX.
    Nodes represent papers (ingested papers + referenced external works).
    Edges (u -> v) mean Paper u cites Paper v.
    """

    def __init__(self, graph_path: Optional[Path] = None):
        self.graph_path = graph_path or settings.citation_graph_path
        self.graph: nx.DiGraph = nx.DiGraph()
        if self.graph_path and self.graph_path.exists():
            self.load()

    def add_paper(self, paper: PaperMetadata) -> None:
        """Add or update a paper node and its outgoing citation edges."""
        self.graph.add_node(
            paper.paper_id,
            title=paper.title,
            authors=paper.authors,
            published_date=str(paper.published_date) if paper.published_date else None,
            citation_count=paper.citation_count,
            categories=paper.categories,
            ingested=True,
        )

        for ref_id in paper.references:
            if not self.graph.has_node(ref_id):
                self.graph.add_node(ref_id, title=f"External Reference ({ref_id})", ingested=False)
            self.graph.add_edge(paper.paper_id, ref_id)

    def remove_paper(self, paper_id: str) -> None:
        """Remove an ingested paper and prune any orphaned external reference nodes."""
        if not self.graph.has_node(paper_id):
            return
        neighbors = list(self.graph.successors(paper_id))
        self.graph.remove_node(paper_id)
        for nb in neighbors:
            if (
                self.graph.has_node(nb)
                and not self.graph.nodes[nb].get("ingested", False)
                and self.graph.degree(nb) == 0
            ):
                self.graph.remove_node(nb)
        self.save()

    def get_related_papers(self, paper_ids: List[str], limit: int = 10) -> List[str]:
        """
        Given a set of retrieved paper IDs, find related papers via the citation graph:
        1. Ingested papers that directly cite or are cited by these papers.
        2. Co-citing ingested papers (papers that share common references with the query papers).
        3. Most frequently cited shared references across the query papers.
        """
        seed_set: Set[str] = {pid for pid in paper_ids if self.graph.has_node(pid)}
        if not seed_set:
            return []

        related_scores: Dict[str, int] = {}

        # 1. Direct citation neighbors & co-citation (shared references)
        seed_references: Set[str] = set()
        for pid in seed_set:
            # Direct outgoing references
            for _, ref_id in self.graph.out_edges(pid):
                seed_references.add(ref_id)
                related_scores[ref_id] = related_scores.get(ref_id, 0) + 1
            # Direct incoming citations
            for citer_id, _ in self.graph.in_edges(pid):
                if citer_id not in seed_set:
                    related_scores[citer_id] = related_scores.get(citer_id, 0) + 3

        # 2. Other ingested papers that cite the same references (bibliographic coupling)
        for ref_id in seed_references:
            for citer_id, _ in self.graph.in_edges(ref_id):
                if citer_id not in seed_set:
                    # Boost ingested papers that share references
                    is_ingested = self.graph.nodes[citer_id].get("ingested", False)
                    boost = 3 if is_ingested else 1
                    related_scores[citer_id] = related_scores.get(citer_id, 0) + boost

        ranked = sorted(related_scores.items(), key=lambda item: item[1], reverse=True)
        results: List[str] = []
        for node_id, score in ranked[:limit]:
            node_data = self.graph.nodes[node_id]
            title = node_data.get("title", node_id)
            if node_data.get("ingested", False):
                results.append(f"[Ingested] {node_id}: {title} (link score: {score})")
            else:
                results.append(f"[Cited Ref] {node_id} (shared citations: {score})")
        return results

    def save(self) -> None:
        """Persist the citation graph to JSON."""
        if not self.graph_path:
            return
        self.graph_path.parent.mkdir(parents=True, exist_ok=True)
        data = nx.node_link_data(self.graph)
        self.graph_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load(self) -> None:
        """Load the citation graph from JSON if available."""
        if self.graph_path and self.graph_path.exists():
            raw = json.loads(self.graph_path.read_text(encoding="utf-8"))
            self.graph = nx.node_link_graph(raw, directed=True)

    def get_stats(self) -> Dict[str, int]:
        """Return summary statistics of the citation graph."""
        ingested_count = sum(
            1 for _, attr in self.graph.nodes(data=True) if attr.get("ingested", False)
        )
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "ingested_papers": ingested_count,
            "external_references": self.graph.number_of_nodes() - ingested_count,
            "total_citation_edges": self.graph.number_of_edges(),
        }

    def resolve_reference_titles(self, max_nodes: int = 40) -> int:
        """
        Batch-resolve human-readable paper titles for external OpenAlex reference IDs (e.g. W2963403868)
        in a single request so the 3D Citation Graph displays real paper titles on every node.
        """
        unresolved = []
        for node_id, attr in self.graph.nodes(data=True):
            if not attr.get("ingested", False):
                cur_title = attr.get("title", "")
                if str(node_id).startswith("W") and (
                    not cur_title or cur_title.startswith("External Reference")
                ):
                    in_deg = self.graph.in_degree(node_id)
                    unresolved.append((in_deg, node_id))

        if not unresolved:
            return 0

        unresolved.sort(reverse=True)
        batch_ids = [nid for _, nid in unresolved[:max_nodes]]
        filter_str = "|".join(batch_ids)
        url = "https://api.openalex.org/works"
        params = {
            "filter": f"openalex_id:{filter_str}",
            "select": "id,display_name,publication_year",
            "per-page": len(batch_ids),
        }

        updated = 0
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, params=params)
                if resp.status_code == 200:
                    for item in resp.json().get("results", []):
                        wid = (item.get("id") or "").split("/")[-1]
                        name = (item.get("display_name") or "").strip()
                        year = item.get("publication_year")
                        if wid and name and self.graph.has_node(wid):
                            label = f"{name} ({year})" if year else name
                            self.graph.nodes[wid]["title"] = label
                            updated += 1
            if updated > 0:
                self.save()
        except Exception:
            pass
        return updated
