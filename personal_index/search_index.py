"""Local search index with full-text search and relevance scoring."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Optional

from personal_index.models import CrawledPage


class SearchIndex:
    """In-memory and persistent full-text search index."""

    def __init__(self, index_path: str = "~/.personal-index/index.json"):
        self._path = Path(index_path).expanduser()
        self._documents: dict[str, CrawledPage] = {}
        self._term_doc_freq: dict[str, int] = {}
        self._doc_lengths: dict[str, int] = {}
        self._load()

    def _load(self) -> None:
        """Load index from disk."""
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text())
                for doc_data in data.get("documents", []):
                    page = CrawledPage(
                        url=doc_data["url"],
                        title=doc_data.get("title", ""),
                        content=doc_data.get("content", ""),
                        meta_description=doc_data.get("meta_description", ""),
                        status_code=doc_data.get("status_code", 0),
                        matched_interests=doc_data.get("matched_interests", []),
                        relevance_score=doc_data.get("relevance_score", 0.0),
                    )
                    self._documents[page.url] = page
                    self._update_term_freq(page)
            except (json.JSONDecodeError, KeyError):
                self._documents.clear()
                self._term_doc_freq.clear()
                self._doc_lengths.clear()

    def _save(self) -> None:
        """Save index to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "documents": [
                {
                    "url": p.url,
                    "title": p.title,
                    "content": p.content,
                    "meta_description": p.meta_description,
                    "status_code": p.status_code,
                    "matched_interests": p.matched_interests,
                    "relevance_score": p.relevance_score,
                }
                for p in self._documents.values()
            ]
        }
        self._path.write_text(json.dumps(data, indent=2))

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Tokenize text into lowercase words."""
        if not text:
            return []
        return re.findall(r'\b[a-z0-9]+\b', text.lower())

    def _update_term_freq(self, page: CrawledPage) -> None:
        """Update term frequency for a document."""
        combined = f"{page.title} {page.content} {page.meta_description}"
        tokens = self._tokenize(combined)
        self._doc_lengths[page.url] = len(tokens)
        term_freq = Counter(tokens)
        for term in term_freq:
            self._term_doc_freq[term] = self._term_doc_freq.get(term, 0) + 1

    def add(self, page: CrawledPage) -> None:
        """Add a page to the index."""
        self._documents[page.url] = page
        self._update_term_freq(page)
        self._save()

    def remove(self, url: str) -> bool:
        """Remove a page from the index."""
        if url in self._documents:
            del self._documents[url]
            self._rebuild_term_freq()
            self._save()
            return True
        return False

    def _rebuild_term_freq(self) -> None:
        """Rebuild term frequency from all documents."""
        self._term_doc_freq.clear()
        self._doc_lengths.clear()
        for page in self._documents.values():
            self._update_term_freq(page)

    def search(self, query: str, limit: int = 20) -> list[tuple[str, float]]:
        """Search the index and return (url, score) pairs sorted by relevance."""
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores: dict[str, float] = {}
        num_docs = max(len(self._documents), 1)

        for token in query_tokens:
            idf = math.log(num_docs / (1 + self._term_doc_freq.get(token, 0)))
            for url, page in self._documents.items():
                combined = f"{page.title} {page.content} {page.meta_description}"
                tokens = self._tokenize(combined)
                tf = tokens.count(token)
                if tf > 0:
                    doc_len = max(self._doc_lengths.get(url, 1), 1)
                    tf_norm = tf / doc_len
                    score = tf_norm * idf
                    # Boost title matches
                    title_tokens = self._tokenize(page.title)
                    if token in title_tokens:
                        score *= 2.0
                    # Boost by interest relevance
                    score += page.relevance_score * 0.1
                    scores[url] = scores.get(url, 0.0) + score

        # Sort by score descending
        results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return results[:limit]

    def get(self, url: str) -> Optional[CrawledPage]:
        """Get a page by URL."""
        return self._documents.get(url)

    def count(self) -> int:
        """Return number of indexed pages."""
        return len(self._documents)

    def clear(self) -> None:
        """Clear the entire index."""
        self._documents.clear()
        self._term_doc_freq.clear()
        self._doc_lengths.clear()
        self._save()

    def urls(self) -> list[str]:
        """Return all indexed URLs."""
        return list(self._documents.keys())
