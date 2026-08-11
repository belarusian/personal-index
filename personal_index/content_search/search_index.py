"""Inverted index for content search."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchIndex:
    """Inverted index mapping terms to document IDs.

    Attributes:
        index: Mapping from term to set of document IDs.
        doc_data: Mapping from document ID to document data.
        doc_terms: Mapping from document ID to set of terms.
    """

    index: dict[str, set[str]] = field(default_factory=dict)
    doc_data: dict[str, dict[str, Any]] = field(default_factory=dict)
    doc_terms: dict[str, set[str]] = field(default_factory=dict)

    def add_document(
        self,
        doc_id: str,
        terms: list[str],
        data: dict[str, Any] | None = None,
    ) -> None:
        """Add a document to the index.

        Args:
            doc_id: Unique document identifier.
            terms: List of terms in the document.
            data: Optional document metadata.
        """
        term_set = set(terms)
        self.doc_terms[doc_id] = term_set
        if data:
            self.doc_data[doc_id] = data

        for term in term_set:
            self.index.setdefault(term, set()).add(doc_id)

    def remove_document(self, doc_id: str) -> None:
        """Remove a document from the index.

        Args:
            doc_id: Document identifier to remove.
        """
        terms = self.doc_terms.pop(doc_id, set())
        self.doc_data.pop(doc_id, None)

        for term in terms:
            if term in self.index:
                self.index[term].discard(doc_id)
                if not self.index[term]:
                    del self.index[term]

    def search(self, terms: list[str]) -> set[str]:
        """Search for documents containing all terms.

        Args:
            terms: List of search terms.

        Returns:
            Set of matching document IDs.
        """
        if not terms:
            return set()

        result: set[str] | None = None
        for term in terms:
            matching = self.index.get(term, set())
            if result is None:
                result = matching.copy()
            else:
                result &= matching
            if not result:
                return set()

        return result or set()

    def search_any(self, terms: list[str]) -> set[str]:
        """Search for documents containing any of the terms.

        Args:
            terms: List of search terms.

        Returns:
            Set of matching document IDs.
        """
        if not terms:
            return set()

        result: set[str] = set()
        for term in terms:
            result |= self.index.get(term, set())
        return result

    def get_document(self, doc_id: str) -> dict[str, Any] | None:
        """Get document data by ID.

        Args:
            doc_id: Document identifier.

        Returns:
            Document data or None if not found.
        """
        return self.doc_data.get(doc_id)

    @property
    def document_count(self) -> int:
        """Number of documents in the index."""
        return len(self.doc_terms)

    @property
    def term_count(self) -> int:
        """Number of unique terms in the index."""
        return len(self.index)
