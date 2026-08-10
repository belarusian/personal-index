"""Search index module for CLI interface."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List


# Common stop words to exclude from indexing
STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "by", "is", "it", "as", "be", "are", "was",
    "were", "this", "that", "from", "not", "no", "do", "does", "did",
    "has", "have", "had", "will", "would", "could", "should", "may",
    "might", "can", "shall", "its", "he", "she", "we", "they", "i",
    "me", "my", "our", "your", "his", "her", "their", "what", "which",
    "who", "when", "where", "how", "all", "each", "every", "both",
    "few", "more", "most", "other", "some", "such", "than", "too",
    "very", "just", "about", "above", "after", "again", "also", "any",
    "because", "before", "between", "during", "if", "into", "only",
    "own", "same", "so", "then", "there", "these", "those", "up",
    "while", "am", "being", "having", "doing", "get", "got",
})


@dataclass
class IndexedPage:
    """A page stored in the search index."""

    url: str
    title: str
    content: str
    keywords: List[str] = field(default_factory=list)
    score: float = 1.0
    indexed_at: str = ""
    source_interest: str = ""
    word_count: int = 0

    def to_dict(self) -> dict:
        """Serialize the index entry to a dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "keywords": self.keywords,
            "score": self.score,
            "indexed_at": self.indexed_at,
            "source_interest": self.source_interest,
            "word_count": self.word_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IndexedPage":
        """Process from_dict.

        Args:
        data.
        """
        return cls(**data)


@dataclass
class SearchResult:
    """A result from a search query."""

    url: str
    title: str
    snippet: str = ""
    relevance_score: float = 0.0


@dataclass
class SearchIndex:
    """Search index with SQLite-like persistence via JSON."""

    db_path: str | None = None
    _pages: Dict[str, IndexedPage] = field(default_factory=dict, repr=False)
    _word_index: Dict[str, List[str]] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        if self.db_path and os.path.exists(self.db_path):
            self._load()

    def _load(self) -> None:
        """Load index from file."""
        try:
            with open(self.db_path, "r") as f:
                data = json.load(f)
            self._pages = {url: IndexedPage.from_dict(d) for url, d in data.get("pages", {}).items()}
            self._word_index = data.get("word_index", {})
        except (json.JSONDecodeError, KeyError, TypeError):
            self._pages = {}
            self._word_index = {}

    def _save(self) -> None:
        """Save index to file."""
        if not self.db_path:
            return
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        data = {
            "pages": {url: page.to_dict() for url, page in self._pages.items()},
            "word_index": self._word_index,
        }
        with open(self.db_path, "w") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Tokenize text into lowercase words, filtering stop words."""
        if not text:
            return []
        words = re.findall(r"[a-z0-9]+", text.lower())
        return [w for w in words if w not in STOP_WORDS and len(w) > 1]

    def add_page(self, page: IndexedPage) -> int:
        """Add a page to the index. Returns page id."""
        self._pages[page.url] = page
        # Build word index
        text = f"{page.title} {page.content}"
        tokens = self._tokenize(text)
        for token in set(tokens):
            if token not in self._word_index:
                self._word_index[token] = []
            if page.url not in self._word_index[token]:
                self._word_index[token].append(page.url)
        self._save()
        return len(self._pages)

    def remove_page(self, url: str) -> bool:
        """Remove a page from the index."""
        if url not in self._pages:
            return False
        # Pop the page to remove it
        page = self._pages.pop(url)
        # text = f"{page.title} {page.content}"
        # tokens = set(self._tokenize(text))
        # Iterate over a copy of keys to avoid RuntimeError
        for token in list(self._word_index.keys()):
            if url in self._word_index[token]:
                self._word_index[token].remove(url)
                if not self._word_index[token]:
                    del self._word_index[token]
        self._save()
        return True

    def get_page(self, url: str) -> IndexedPage | None:
        """Get a page by URL."""
        return self._pages.get(url)

    def get_page_count(self) -> int:
        """Get number of indexed pages."""
        return len(self._pages)

    def list_pages(self) -> List[IndexedPage]:
        """List all pages sorted by score."""
        return sorted(self._pages.values(), key=lambda p: p.score, reverse=True)

    def clear(self) -> None:
        """Clear the index."""
        self._pages = {}
        self._word_index = {}
        self._save()

    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search the index."""
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
                        scores[url] += title_count * 3.0 + content_count * 1.0
                        scores[url] += page.score * 0.5

        results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        search_results = []
        for url, score in results[:limit]:
            page = self._pages.get(url)
            if page:
                snippet = self._create_snippet(page.content, query)
                search_results.append(SearchResult(
                    url=url,
                    title=page.title,
                    snippet=snippet,
                    relevance_score=score,
                ))
        return search_results

    def _create_snippet(self, content: str, query: str, length: int = 150) -> str:
        """Create a snippet highlighting the query."""
        if not content:
            return ""
        query_lower = query.lower()
        idx = content.lower().find(query_lower)
        if idx == -1:
            return content[:length] + ("..." if len(content) > length else "")
        start = max(0, idx - 50)
        end = min(len(content), idx + len(query) + length)
        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
        return snippet

    def close(self) -> None:
        """Close the index (save)."""
        self._save()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
