"""Full-text search with ranking for personal-index content."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Optional


# Common English stopwords
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "need", "dare",
    "it", "its", "this", "that", "these", "those", "i", "you", "he", "she",
    "we", "they", "what", "which", "who", "whom", "when", "where", "why",
    "how", "all", "each", "every", "both", "few", "more", "most", "other",
    "some", "such", "no", "not", "only", "own", "same", "so", "than", "too",
    "very", "just", "about", "above", "after", "again", "also", "any",
    "because", "before", "between", "during", "if", "into", "like", "new",
    "now", "old", "over", "then", "there", "here", "up", "out", "off",
}


class Tokenizer:
    """Tokenizes text into searchable terms."""

    @staticmethod
    def tokenize(text: str) -> list[str]:
        """Tokenize text into lowercase words, removing stopwords."""
        if not text:
            return []
        tokens = re.findall(r'[a-z0-9]+', text.lower())
        return [t for t in tokens if t not in STOPWORDS]


class BM25Ranker:
    """BM25 ranking algorithm for document scoring."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        """Initialize BM25 ranker with tuning parameters.

        Args:
            k1: Term frequency saturation parameter.
            b: Document length normalization parameter.
        """
        self.k1 = k1
        self.b = b

    def compute_score(
        self,
        tokens: list[str],
        doc_freq: dict[str, int],
        total_docs: int,
        doc_len: int,
        avg_len: float,
    ) -> float:
        """Compute BM25 score for a document given query tokens."""
        if not tokens or total_docs == 0:
            return 0.0

        score = 0.0
        for token in tokens:
            df = doc_freq.get(token, 0)
            if df == 0:
                continue
            # IDF component
            idf = math.log(
                (total_docs - df + 0.5) / (df + 0.5) + 1.0
            )
            # TF component (simplified - assumes term appears in doc)
            tf = doc_freq[token]
            tf_score = (tf * (self.k1 + 1)) / (
                tf + self.k1 * (1 - self.b + self.b * doc_len / avg_len)
            )
            score += idf * tf_score
        return score


@dataclass
class SearchResult:
    """A single search result."""

    content_id: str
    score: float
    title: str = ""
    snippet: Optional[str] = None
    content_type: str = ""
    url: str = ""
    date: str = ""

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "content_id": self.content_id,
            "score": self.score,
            "title": self.title,
            "snippet": self.snippet,
            "content_type": self.content_type,
            "url": self.url,
            "date": self.date,
        }


@dataclass
class SearchResults:
    """Collection of search results with metadata."""

    results: list[SearchResult] = field(default_factory=list)
    total_count: int = 0
    query: str = ""
    limit: int = 20
    offset: int = 0
    has_next: bool = False

    def __len__(self) -> int:
        """Return number of results."""
        return len(self.results)

    def __iter__(self):
        """Iterate over results."""
        return iter(self.results)

    def __getitem__(self, index):
        """Access result by index."""
        return self.results[index]

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "results": [r.to_dict() for r in self.results],
            "total_count": self.total_count,
            "query": self.query,
            "limit": self.limit,
            "offset": self.offset,
            "has_next": self.has_next,
        }


@dataclass
class SearchQuery:
    """A search query with optional filters."""

    query: str
    limit: int = 20
    offset: int = 0
    content_type: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    url_pattern: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "query": self.query,
            "limit": self.limit,
            "offset": self.offset,
            "content_type": self.content_type,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "url_pattern": self.url_pattern,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SearchQuery":
        """Deserialize from dictionary."""
        return cls(
            query=data.get("query", ""),
            limit=data.get("limit", 20),
            offset=data.get("offset", 0),
            content_type=data.get("content_type"),
            date_from=data.get("date_from"),
            date_to=data.get("date_to"),
            url_pattern=data.get("url_pattern"),
        )


class SearchIndex:
    """Full-text search index with BM25 ranking."""

    def __init__(self) -> None:
        """Initialize the full-text search index with empty storage."""
        self._documents: dict[str, dict] = {}
        self._inverted_index: dict[str, dict[str, int]] = {}
        self._doc_lengths: dict[str, int] = {}
        self._tokenizer = Tokenizer()
        self._ranker = BM25Ranker()

    def add_document(
        self,
        content_id: str,
        content: str,
        title: str = "",
        content_type: str = "",
        url: str = "",
        date: str = "",
        metadata: Optional[dict] = None,
    ) -> None:
        """Add or update a document in the index."""
        # Store document
        self._documents[content_id] = {
            "content_id": content_id,
            "content": content,
            "title": title,
            "content_type": content_type,
            "url": url,
            "date": date,
            "metadata": metadata or {},
        }

        # Tokenize content and title
        content_tokens = self._tokenizer.tokenize(content)
        title_tokens = self._tokenizer.tokenize(title)

        # Build inverted index
        doc_freq: dict[str, int] = {}
        for token in content_tokens:
            doc_freq[token] = doc_freq.get(token, 0) + 1
        for token in title_tokens:
            doc_freq[token] = doc_freq.get(token, 0) + 1

        self._doc_lengths[content_id] = len(content_tokens) + len(title_tokens)

        for token, freq in doc_freq.items():
            if token not in self._inverted_index:
                self._inverted_index[token] = {}
            self._inverted_index[token][content_id] = freq

    def update_document(
        self,
        content_id: str,
        content: str,
        title: str = "",
        content_type: str = "",
        url: str = "",
        date: str = "",
        metadata: Optional[dict] = None,
    ) -> bool:
        """Update an existing document."""
        if content_id not in self._documents:
            return False
        self.remove_document(content_id)
        self.add_document(content_id, content, title, content_type, url, date, metadata)
        return True

    def remove_document(self, content_id: str) -> None:
        """Remove a document from the index."""
        doc = self._documents.pop(content_id, None)
        if not doc:
            return
        content_tokens = self._tokenizer.tokenize(doc.get("content", ""))
        title_tokens = self._tokenizer.tokenize(doc.get("title", ""))
        all_tokens = content_tokens + title_tokens
        for token in set(all_tokens):
            if token in self._inverted_index:
                self._inverted_index[token].pop(content_id, None)
                if not self._inverted_index[token]:
                    del self._inverted_index[token]
        self._doc_lengths.pop(content_id, None)

    def search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        content_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        url_pattern: Optional[str] = None,
        boost_title: float = 1.0,
    ) -> SearchResults:
        """Search the index and return ranked results."""
        tokens = self._tokenizer.tokenize(query)
        if not tokens:
            return SearchResults(total_count=0, query=query, limit=limit, offset=offset)

        # Find candidate documents
        candidate_ids: set[str] = set()
        for token in tokens:
            if token in self._inverted_index:
                candidate_ids.update(self._inverted_index[token].keys())

        if not candidate_ids:
            return SearchResults(total_count=0, query=query, limit=limit, offset=offset)

        # Score each candidate
        total_docs = len(self._documents)
        avg_len = (
            sum(self._doc_lengths.values()) / len(self._doc_lengths)
            if self._doc_lengths
            else 1
        )

        scored: list[tuple[float, str]] = []
        for doc_id in candidate_ids:
            doc = self._documents.get(doc_id)
            if not doc:
                continue

            # Apply filters
            if content_type and doc.get("content_type") != content_type:
                continue
            if date_from and doc.get("date", "") < date_from:
                continue
            if date_to and doc.get("date", "") > date_to:
                continue
            if url_pattern and url_pattern not in doc.get("url", ""):
                continue

            # Compute BM25 score
            doc_len = self._doc_lengths.get(doc_id, 1)

            score = 0.0
            for token in tokens:
                if token in self._inverted_index and doc_id in self._inverted_index[token]:
                    tf = self._inverted_index[token][doc_id]
                    df = len(self._inverted_index[token])
                    idf = math.log(
                        (total_docs - df + 0.5) / (df + 0.5) + 1.0
                    )
                    tf_score = (tf * (self._ranker.k1 + 1)) / (
                        tf + self._ranker.k1 * (1 - self._ranker.b + self._ranker.b * doc_len / avg_len)
                    )
                    score += idf * tf_score

            # Boost title matches
            title_tokens = self._tokenizer.tokenize(doc.get("title", ""))
            for token in tokens:
                if token in title_tokens:
                    score *= boost_title

            if score > 0:
                scored.append((score, doc_id))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        total_count = len(scored)
        paginated = scored[offset: offset + limit]

        results = []
        for score, doc_id in paginated:
            doc = self._documents[doc_id]
            snippet = self._generate_snippet(doc.get("content", ""), tokens)
            results.append(
                SearchResult(
                    content_id=doc_id,
                    score=round(score, 4),
                    title=doc.get("title", ""),
                    snippet=snippet,
                    content_type=doc.get("content_type", ""),
                    url=doc.get("url", ""),
                    date=doc.get("date", ""),
                )
            )

        return SearchResults(
            results=results,
            total_count=total_count,
            query=query,
            limit=limit,
            offset=offset,
            has_next=(offset + limit) < total_count,
        )

    def search_query(self, query: SearchQuery) -> SearchResults:
        """Search using a SearchQuery object."""
        return self.search(
            query=query.query,
            limit=query.limit,
            offset=query.offset,
            content_type=query.content_type,
            date_from=query.date_from,
            date_to=query.date_to,
            url_pattern=query.url_pattern,
        )

    def _generate_snippet(
        self, content: str, tokens: list[str], max_length: int = 150
    ) -> Optional[str]:
        """Generate a snippet highlighting search terms."""
        if not content or not tokens:
            return None

        # Find first occurrence of any token
        best_pos = -1
        for token in tokens:
            pos = content.lower().find(token)
            if pos != -1 and (best_pos == -1 or pos < best_pos):
                best_pos = pos

        if best_pos == -1:
            return content[:max_length] + "..." if len(content) > max_length else content

        start = max(0, best_pos - 50)
        end = min(len(content), best_pos + max_length)
        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
        return snippet

    def get_document(self, content_id: str) -> Optional[dict]:
        """Get a document by ID."""
        return self._documents.get(content_id)

    def get_all_ids(self) -> list[str]:
        """Get all document IDs."""
        return list(self._documents.keys())

    def doc_count(self) -> int:
        """Return the number of indexed documents."""
        return len(self._documents)

    def clear(self) -> None:
        """Clear the entire index."""
        self._documents.clear()
        self._inverted_index.clear()
        self._doc_lengths.clear()

    def get_stats(self) -> dict:
        """Get index statistics."""
        total_terms = sum(len(docs) for docs in self._inverted_index.values())
        return {
            "total_documents": len(self._documents),
            "total_terms": len(self._inverted_index),
            "total_term_occurrences": total_terms,
        }

    def serialize(self) -> dict:
        """Serialize the index."""
        return {
            "documents": self._documents,
            "inverted_index": self._inverted_index,
            "doc_lengths": self._doc_lengths,
        }

    def deserialize(self, data: dict) -> None:
        """Deserialize the index."""
        self.clear()
        self._documents = data.get("documents", {})
        self._inverted_index = data.get("inverted_index", {})
        self._doc_lengths = data.get("doc_lengths", {})
