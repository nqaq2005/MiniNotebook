from typing import List, TypedDict
from src.models.schemas import RetrievedPassage


class ResearchAgentState(TypedDict, total=False):
    """State dictionary passed across nodes in the Agentic Literature Review workflow."""

    question: str
    sub_queries: List[str]
    retrieved_passages: List[RetrievedPassage]
    related_papers_from_graph: List[str]
    draft_answer: str
    is_grounded: bool
    grounding_score: float
    verification_notes: str
