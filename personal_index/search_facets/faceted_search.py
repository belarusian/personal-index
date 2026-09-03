"""Faceted search engine with filterable dimensions."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
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
            if isinstance(value, (list, str, int, float, bool)):
                facets.add(key)
        return sorted(facets)

    def clear(self) -> None:
        """Clear all documents."""
        self._documents.clear()

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

        if query.strip():
            docs = self._apply_text_search(docs, query)

        if filters:
            docs = [d for d in docs if self._matches_all_filters(d, filters)]

        total = len(docs)
        start = (page - 1) * page_size
        paginated = docs[start : start + page_size]

        facets: dict[str, Facet] = {}
        if facet_fields:
            facets = self._facet_builder.build(docs, facet_fields)

        return SearchResults(
            results=paginated,
            facets=facets,
            total=total,
            page=page,
            page_size=page_size,
        )

    def _apply_text_search(
        self, docs: list[dict[str, Any]], query: str
    ) -> list[dict[str, Any]]:
        """Score and sort documents by text query match."""
        query_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
        scored: list[tuple[dict[str, Any], float]] = []

        for doc in docs:
            text = self._extract_text(doc)
            tokens = set(re.findall(r"[a-z0-9]+", text))
            if query_tokens & tokens:
                score = len(query_tokens & tokens) / len(query_tokens) if query_tokens else 0
                scored.append((doc, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [d for d, _ in scored]

    def _get_nested_value(self, doc: dict[str, Any], field_name: str) -> Any:
        """Get a value from a document, supporting nested dot notation."""
        parts = field_name.split(".")
        current: Any = doc
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    def _matches_all_filters(
        self, doc: dict[str, Any], filters: dict[str, Any]
    ) -> bool:
        """Check if a document matches all filters."""
        for field_name, filter_value in filters.items():
            doc_value = self._get_nested_value(doc, field_name)

            if isinstance(filter_value, dict):
                # Range or special filter operators
                if not self._matches_range_filter(doc_value, filter_value):
                    return False
            elif isinstance(filter_value, list):
                # List filter: doc value must be in the list
                if isinstance(doc_value, list):
                    if not set(doc_value) & set(filter_value):
                        return False
                else:
                    if doc_value not in filter_value:
                        return False
            else:
                # Exact match (case-insensitive for strings)
                if isinstance(doc_value, str) and isinstance(filter_value, str):
                    if doc_value.lower() != filter_value.lower():
                        return False
                elif doc_value != filter_value:
                    return False
        return True

    def _matches_range_filter(
        self, doc_value: Any, filter_spec: dict[str, Any]
    ) -> bool:
        """Check if a value matches a range filter specification."""
        if doc_value is None:
            return False

        parsed = self._parse_date_value(doc_value)
        if parsed is None:
            parsed = doc_value

        if not self._check_between(parsed, filter_spec):
            return False
        if not self._check_gte(parsed, filter_spec):
            return False
        if not self._check_lte(parsed, filter_spec):
            return False
        if not self._check_gt(parsed, filter_spec):
            return False
        if not self._check_lt(parsed, filter_spec):
            return False
        if not self._check_in(parsed, filter_spec):
            return False
        return self._check_not(parsed, filter_spec)

    def _check_between(self, val: Any, spec: dict[str, Any]) -> bool:
        if "$between" not in spec:
            return True
        between = spec["$between"]
        if not isinstance(between, (list, tuple)) or len(between) != 2:
            return True
        low, high = between
        lp, hp = self._parse_date_value(low), self._parse_date_value(high)
        if lp is not None and hp is not None:
            return bool(lp <= val <= hp)
        return bool(low <= val <= high)

    def _check_gte(self, val: Any, spec: dict[str, Any]) -> bool:
        if "$gte" not in spec:
            return True
        pv = self._parse_date_value(spec["$gte"])
        if pv is not None:
            return bool(val >= pv)
        return bool(val >= spec["$gte"])

    def _check_lte(self, val: Any, spec: dict[str, Any]) -> bool:
        if "$lte" not in spec:
            return True
        pv = self._parse_date_value(spec["$lte"])
        if pv is not None:
            return bool(val <= pv)
        return bool(val <= spec["$lte"])

    def _check_gt(self, val: Any, spec: dict[str, Any]) -> bool:
        if "$gt" not in spec:
            return True
        pv = self._parse_date_value(spec["$gt"])
        if pv is not None:
            return bool(val > pv)
        return bool(val > spec["$gt"])

    def _check_lt(self, val: Any, spec: dict[str, Any]) -> bool:
        if "$lt" not in spec:
            return True
        pv = self._parse_date_value(spec["$lt"])
        if pv is not None:
            return bool(val < pv)
        return bool(val < spec["$lt"])

    def _check_in(self, val: Any, spec: dict[str, Any]) -> bool:
        if "$in" not in spec:
            return True
        in_list = spec["$in"]
        if isinstance(in_list, (list, set)):
            return val in in_list
        return True

    def _check_not(self, val: Any, spec: dict[str, Any]) -> bool:
        if "$not" not in spec:
            return True
        return bool(val != spec["$not"])

    def _parse_date_value(self, value: Any) -> Any:
        """Parse a value as a date if it's a date-like string.

        Returns a datetime object for ISO format strings, the original value
        for numbers (and datetimes), and None for any other value, including
        strings that are not parseable as an ISO date. Callers treat the None
        return as the "not a date" sentinel.
        """
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            # Try ISO format date parsing
            try:
                return datetime.fromisoformat(value)
            except (ValueError, TypeError):
                pass
        return None
