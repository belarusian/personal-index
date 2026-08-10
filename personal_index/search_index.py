"""Local search index with full-text search and relevance scoring."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from personal_index.models import CrawledPage


@dataclass
class SearchIndex:
    """In-memory search index with JSON persistence."""

    index_path: str
    _pages: Dict[str, CrawledPage] = field(default_factory=dict, repr=False)
    _word_index: Dict[str, List[str]] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        self._load()

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Tokenize text into lowercase words, removing punctuation."""
        if not text:
            return []
        return re.findall(r"[a-z0-9]+", text.lower())

    def _load(self) -> None:
        """Load index from file."""
        if not os.path.exists(self.index_path):
            self._pages = {}
            self._word_index = {}
            return
        try:
            with open(self.index_path, "r") as f:
                data = json.load(f)
            self._pages = {}
            for url, page_data in data.get("pages", {}).items():
                page = CrawledPage(**page_data)
                self._pages[url] = page
            self._word_index = data.get("word_index", {})
        except (json.JSONDecodeError, KeyError):
            self._pages = {}
            self._word_index = {}

    def _save(self) -> None:
        """Save index to file."""
        parent = Path(self.index_path).parent
        parent.mkdir(parents=True, exist_ok=True)
        pages_data = {}
        for url, page in self._pages.items():
            pages_data[url] = {
                "url": page.url,
                "title": page.title,
                "content": page.content,
                "meta_description": page.meta_description,
                "status_code": page.status_code,
                "depth": page.depth,
                "parent_url": page.parent_url,
                "headers": page.headers,
                "matched_interests": page.matched_interests,
                "relevance_score": page.relevance_score,
                "crawled_at": page.crawled_at.isoformat(),
            }
        data = {"pages": pages_data, "word_index": self._word_index}
        with open(self.index_path, "w") as f:
            json.dump(data, f, indent=2)

    def add(self, page: CrawledPage) -> None:
        """Add a page to the index."""
        self._pages[page.url] = page
        text = f"{page.title} {page.content}".lower()
        tokens = self._tokenize(text)
        for token in set(tokens):
            if token not in self._word_index:
                self._word_index[token] = []
            if page.url not in self._word_index[token]:
                self._word_index[token].append(page.url)
        self._save()

    def remove(self, url: str) -> bool:
        """Remove a page from the index."""
        if url not in self._pages:
            return False
        # page = self._pages.pop(url)
        # text = f"{page.title} {page.content}".lower()
        # tokens = set(self._tokenize(text))
        # Iterate over a copy of keys to avoid RuntimeError
        for token in list(self._word_index.keys()):
            if url in self._word_index[token]:
                self._word_index[token].remove(url)
                if not self._word_index[token]:
                    del self._word_index[token]
        self._save()
        return True

    def get(self, url: str) -> Optional[CrawledPage]:
        """Get a page by URL."""
        return self._pages.get(url)

    def count(self) -> int:
        """Return number of indexed pages."""
        return len(self._pages)

    def clear(self) -> None:
        """Clear the entire index."""
        self._pages = {}
        self._word_index = {}
        self._save()

    def urls(self) -> List[str]:
        """Return list of all indexed URLs."""
        return list(self._pages.keys())

    def search(
        self, query: str, limit: int = 10
    ) -> List[Tuple[str, float]]:
        """Search and return (url, score) tuples by relevance."""
        if not query:
            return []
        tokens = self._tokenize(query)
        if not tokens:
            return []

        scores: Dict[str, float] = {}
        for token in tokens:
            if token in self._word_index:
                for url in self._word_index[token]:
                    if url not in scores:
                        scores[url] = 0.0
                    page = self._pages.get(url)
                    if page:
                        title_count = page.title.lower().count(token)
                        content_count = page.content.lower().count(token)
                        scores[url] += title_count * 3.0
                        scores[url] += content_count * 1.0
                        scores[url] += page.relevance_score * 0.5

        results = sorted(
            scores.items(), key=lambda x: x[1], reverse=True
        )
        return results[:limit]
