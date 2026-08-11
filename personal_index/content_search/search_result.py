"""Search result data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchResult:
    """A single search result.

    Attributes:
        doc_id: Document identifier.
        score: Relevance score (0.0 to 1.0).
        data: Document metadata.
        matched_terms: Terms that matched in this document.
        highlight: Highlighted text snippet.
    """

    doc_id: str
    score: float
    data: dict[str, Any] = field(default_factory=dict)
    matched_terms: list[str] = field(default_factory=list)
    highlight: str = ""


@dataclass
class SearchResponse:
    """Complete search response.

    Attributes:
        results: List of search results.
        total_matches: Total number of matching documents.
        query: Original search query.
        elapsed_ms: Search time in milliseconds.
    """

    results: list[SearchResult]
    total_matches: int
    query: str
    elapsed_ms: float = 0.0
