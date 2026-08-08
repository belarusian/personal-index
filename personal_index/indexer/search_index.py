"""Full-text search index with relevance scoring.

Implements an inverted index for efficient full-text search over crawled pages.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from personal_index.models import Page
from personal_index.utils import tokenize


@dataclass
class SearchResult:
    """A single search result."""

    page: Page
    score: float
    matched_terms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "url": self.page.url,
            "title": self.page.title,
            "meta_description": self.page.meta_description,
            "score": self.score,
            "matched_terms": self.matched_terms,
            "matched_interests": self.page.matched_interests,
            "crawled_at": self.page.crawled_at.isoformat() if self.page.crawled_at else None,
        }


class SearchIndex:
    """Inverted index for full-text search with TF-IDF scoring."""

    def __init__(self, index_dir: Optional[Path] = None) -> None:
        """Initialize the search index.

        Args:
            index_dir: Directory to store the index. If None, index is in-memory only.
        """
        self.index_dir = index_dir
        # Inverted index: term -> {page_id: tf}
        self._term_index: dict[str, dict[str, float]] = defaultdict(dict)
        # Document store: page_id -> Page
        self._documents: dict[str, Page] = {}
        # Term frequency per document
        self._doc_lengths: dict[str, int] = {}
        # Number of documents containing each term
        self._doc_freq: dict[str, int] = defaultdict(int)
        self._num_docs = 0

    @property
    def num_documents(self) -> int:
        """Number of indexed documents."""
        return self._num_docs

    @property
    def num_terms(self) -> int:
        """Number of unique terms in the index."""
        return len(self._term_index)

    def add_page(self, page: Page) -> None:
        """Add a page to the index.

        Args:
            page: The page to index.
        """
        page_id = page.id
        text = page.title + " " + page.meta_description + " " + page.content
        tokens = tokenize(text)

        if not tokens:
            return

        # Calculate term frequencies
        tf: dict[str, int] = defaultdict(int)
        for token in tokens:
            tf[token] += 1

        # Update inverted index
        for term, count in tf.items():
            # Normalize TF
            normalized_tf = count / max(len(tokens), 1)

            if page_id not in self._term_index[term]:
                self._doc_freq[term] += 1

            self._term_index[term][page_id] = normalized_tf

        # Store document
        self._documents[page_id] = page
        self._doc_lengths[page_id] = len(tokens)
        self._num_docs = len(self._documents)

    def remove_page(self, page_id: str) -> bool:
        """Remove a page from the index.

        Args:
            page_id: The ID of the page to remove.

        Returns:
            True if the page was removed.
        """
        if page_id not in self._documents:
            return False

        del self._documents[page_id]
        if page_id in self._doc_lengths:
            del self._doc_lengths[page_id]

        # Collect terms to remove (avoid modifying dict during iteration)
        terms_to_update = [term for term in self._term_index if page_id in self._term_index[term]]

        for term in terms_to_update:
            del self._term_index[term][page_id]
            self._doc_freq[term] -= 1
            if self._doc_freq[term] <= 0:
                del self._doc_freq[term]
                if not self._term_index[term]:
                    del self._term_index[term]

        self._num_docs = len(self._documents)
        return True

    def search(
        self,
        query: str,
        limit: int = 20,
        min_score: float = 0.0,
        interest_filter: Optional[list[str]] = None,
    ) -> list[SearchResult]:
        """Search the index for a query.

        Args:
            query: The search query.
            limit: Maximum number of results to return.
            min_score: Minimum relevance score threshold.
            interest_filter: Optional list of interest topics to filter by.

        Returns:
            List of search results sorted by relevance.
        """
        query_terms = tokenize(query)
        if not query_terms:
            return []

        # Score all matching documents
        scores: dict[str, float] = defaultdict(float)
        matched_terms: dict[str, set[str]] = defaultdict(set)

        for term in query_terms:
            if term not in self._term_index:
                continue

            # IDF: log(N / df)
            idf = math.log(1 + self._num_docs / max(self._doc_freq.get(term, 1), 1))

            for page_id, tf in self._term_index[term].items():
                # TF-IDF score
                score = tf * idf
                scores[page_id] += score
                matched_terms[page_id].add(term)

        # Build results
        results = []
        for page_id, score in scores.items():
            if score < min_score:
                continue

            page = self._documents.get(page_id)
            if not page:
                continue

            # Apply interest filter
            if interest_filter:
                if not any(i in page.matched_interests for i in interest_filter):
                    continue

            # Normalize score by document length
            doc_len = max(self._doc_lengths.get(page_id, 1), 1)
            normalized_score = score / math.sqrt(doc_len)

            results.append(
                SearchResult(
                    page=page,
                    score=round(normalized_score, 4),
                    matched_terms=list(matched_terms.get(page_id, set())),
                )
            )

        # Sort by score descending, then by URL for stability
        results.sort(key=lambda r: (-r.score, r.page.url))
        return results[:limit]

    def save(self) -> None:
        """Save the index to disk."""
        if not self.index_dir:
            return

        self.index_dir.mkdir(parents=True, exist_ok=True)

        # Save inverted index
        index_data = {
            "term_index": dict(self._term_index),
            "doc_freq": dict(self._doc_freq),
            "doc_lengths": self._doc_lengths,
            "num_docs": self._num_docs,
        }
        with open(self.index_dir / "index.json", "w") as f:
            json.dump(index_data, f)

        # Save documents
        docs_data = {pid: page.to_dict() for pid, page in self._documents.items()}
        with open(self.index_dir / "documents.json", "w") as f:
            json.dump(docs_data, f)

    def load(self) -> None:
        """Load the index from disk."""
        if not self.index_dir:
            return

        index_file = self.index_dir / "index.json"
        docs_file = self.index_dir / "documents.json"

        if not index_file.exists():
            return

        with open(index_file) as f:
            data = json.load(f)

        self._term_index = defaultdict(dict, data.get("term_index", {}))
        self._doc_freq = defaultdict(int, data.get("doc_freq", {}))
        self._doc_lengths = data.get("doc_lengths", {})
        self._num_docs = data.get("num_docs", 0)

        if docs_file.exists():
            with open(docs_file) as f:
                docs_data = json.load(f)
            self._documents = {
                pid: Page.from_dict(data) for pid, data in docs_data.items()
            }

    def get_page(self, page_id: str) -> Optional[Page]:
        """Get a page by its ID.

        Args:
            page_id: The page ID.

        Returns:
            The page if found, None otherwise.
        """
        return self._documents.get(page_id)

    def get_all_pages(self) -> list[Page]:
        """Get all indexed pages.

        Returns:
            List of all indexed pages.
        """
        return list(self._documents.values())

    def clear(self) -> None:
        """Clear the entire index."""
        self._term_index.clear()
        self._documents.clear()
        self._doc_lengths.clear()
        self._doc_freq.clear()
        self._num_docs = 0
