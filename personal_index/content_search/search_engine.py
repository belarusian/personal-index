"""Search engine for content items."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from personal_index.content_search.search_index import SearchIndex
from personal_index.content_search.search_result import SearchResult, SearchResponse
from personal_index.content_search.tokenizer import Tokenizer


@dataclass
class SearchEngine:
    """Full-text search engine for content items.

    Attributes:
        index: The inverted search index.
        tokenizer: Tokenizer for query and document text.
        max_results: Maximum number of results to return.
    """

    index: SearchIndex = field(default_factory=SearchIndex)
    tokenizer: Tokenizer = field(default_factory=Tokenizer)
    max_results: int = 50

    def index_document(
        self,
        doc_id: str,
        text: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Index a document for search.

        Args:
            doc_id: Unique document identifier.
            text: Full text to index.
            data: Optional document metadata.
        """
        terms = self.tokenizer.tokenize(text)
        self.index.add_document(doc_id, terms, data)

    def remove_document(self, doc_id: str) -> None:
        """Remove a document from the search index.

        Args:
            doc_id: Document identifier to remove.
        """
        self.index.remove_document(doc_id)

    def search(
        self,
        query: str,
        *,
        match_all: bool = True,
        limit: int | None = None,
    ) -> SearchResponse:
        """Search for documents matching the query.

        Args:
            query: Search query string.
            match_all: If True, all terms must match.
            limit: Maximum number of results.

        Returns:
            SearchResponse with results.
        """
        terms = self.tokenizer.tokenize(query)
        if not terms:
            return SearchResponse(results=[], total_matches=0, query=query)

        if match_all:
            doc_ids = self.index.search(terms)
        else:
            doc_ids = self.index.search_any(terms)

        # Score and create results
        results = []
        for doc_id in doc_ids:
            doc_terms = self.index.doc_terms.get(doc_id, set())
            matched = [t for t in terms if t in doc_terms]
            score = len(matched) / len(terms) if terms else 0.0

            data = self.index.get_document(doc_id) or {}
            results.append(
                SearchResult(
                    doc_id=doc_id,
                    score=round(score, 4),
                    data=data,
                    matched_terms=matched,
                )
            )

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)

        max_r = limit or self.max_results
        return SearchResponse(
            results=results[:max_r],
            total_matches=len(doc_ids),
            query=query,
        )

    def index_items(
        self,
        items: list[dict[str, Any]],
        text_fields: list[str] | None = None,
        id_field: str = "id",
    ) -> int:
        """Batch index content items.

        Args:
            items: List of content item dictionaries.
            text_fields: Fields to extract text from.
            id_field: Field name for document ID.

        Returns:
            Number of items indexed.
        """
        if text_fields is None:
            text_fields = ["title", "content", "description", "summary"]

        count = 0
        for item in items:
            doc_id = str(item.get(id_field, ""))
            if not doc_id:
                continue

            text_parts = [
                str(item.get(f, ""))
                for f in text_fields
                if item.get(f)
            ]
            text = " ".join(text_parts)

            if text:
                self.index_document(doc_id, text, item)
                count += 1

        return count
