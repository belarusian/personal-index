"""Faceted search engine with filterable dimensions."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from personal_index.search_facets.facet import Facet
from personal_index.search_facets.facet_builder import FacetBuilder


@dataclass
class SearchResults:
    """Container for faceted search results."""

    results: list[dict[str, Any]] = field(default_factory=list)
    facets: dict[str, Facet] = field(default_factory=dict)
    total: int = 0
    page: int = 1
    page_size: int = 20

    def __getitem__(self, key: str) -> Any:
        """Allow dict-style access."""
        return getattr(self, key)

    def __contains__(self, key: object) -> bool:
        """Allow 'in' operator for dict-style checks."""
        if isinstance(key, str):
            return hasattr(self, key)
        return False

    def keys(self) -> list[str]:
        """Return available keys."""
        return ["results", "facets", "total", "page", "page_size"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "results": self.results,
            "facets": {k: v.to_dict() for k, v in self.facets.items()},
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
        }


class FacetedSearch:
    """Search engine with filterable facet dimensions."""

    def __init__(self) -> None:
        self._documents: dict[str, dict[str, Any]] = {}
        self._facet_builder = FacetBuilder()

    def add_document(self, doc_id: str, data: dict[str, Any]) -> None:
        """Add a document to the search index."""
        self._documents[doc_id] = {
            "id": doc_id,
            **data,
        }

    def remove_document(self, doc_id: str) -> None:
        """Remove a document from the search index."""
        self._documents.pop(doc_id, None)

    def get_documents(self) -> list[dict[str, Any]]:
        """Get all indexed documents."""
        return list(self._documents.values())

    def get_available_facets(self) -> list[str]:
        """Get list of available facet fields."""
        if not self._documents:
            return []
        sample = next(iter(self._documents.values()))
        facets: set[str] = set()
        for key, value in sample.items():
            if key == "id":
                continue
            if isinstance(value, list):
                facets.add(key)
            elif isinstance(value, (str, int, float, bool)):
                facets.add(key)
        return sorted(facets)

    def _extract_text(self, doc: dict[str, Any]) -> str:
        """Extract searchable text from a document."""
        parts: list[str] = []
        for v in doc.values():
            if isinstance(v, str):
                parts.append(v)
            elif isinstance(v, list):
                parts.extend(str(i) for i in v if isinstance(i, str))
        return " ".join(parts).lower()

    def search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        facet_fields: list[str] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SearchResults:
        """Search with optional filters and facets."""
        docs = list(self._documents.values())

        # Apply text search
        if query.strip():
            query_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
            scored: list[tuple[dict[str, Any], float]] = []

            for doc in docs:
                text = self._extract_text(doc)
                tokens = set(re.findall(r"[a-z0-9]+", text))
                if query_tokens & tokens:
                    score = len(query_tokens & tokens) / len(query_tokens) if query_tokens else 0
                    scored.append((doc, score))

            scored.sort(key=lambda x: x[1], reverse=True)
            docs = [d for d, _ in scored]

        # Apply filters
        if filters:
            filtered: list[dict[str, Any]] = []
            for doc in docs:
                match = True
                for field_name, filter_value in filters.items():
                    doc_value = self._get_nested_value(doc, field_name)
                    if isinstance(filter_value, list):
                        if doc_value not in filter_value:
                            match = False
                            break
                    elif isinstance(doc_value, list):
                        if filter_value not in doc_value:
                            match = False
                            break
                    else:
                        if str(doc_value).lower() != str(filter_value).lower():
                            match = False
                            break
                if match:
                    filtered.append(doc)
            docs = filtered

        total = len(docs)

        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated = docs[start:end]

        # Build facets from filtered results
        facets: dict[str, Facet] = {}
        if facet_fields:
            facets = self._facet_builder.build(docs, facet_fields)
        else:
            available = self.get_available_facets()
            if available:
                facets = self._facet_builder.build(docs, available)

        return SearchResults(
            results=paginated,
            facets=facets,
            total=total,
            page=page,
            page_size=page_size,
        )

    def clear(self) -> None:
        """Clear all documents."""
        self._documents.clear()

    def _get_nested_value(self, doc: dict[str, Any], field_name: str) -> Any:
        """Get a nested value from a document."""
        parts = field_name.split(".")
        current: Any = doc
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current
