"""Search index module for CLI interface."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

from personal_index.models import CrawledPage, IndexedPage, SearchResult

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


# Re-export for backward compatibility
__all__ = ["IndexedPage", "SearchIndex", "SearchResult"]


@dataclass
class SearchIndex:
    """Search index with JSON persistence."""

    db_path: str | None = None
    _pages: dict[str, IndexedPage] = field(default_factory=dict, repr=False)
    _word_index: dict[str, list[str]] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        if self.db_path and os.path.exists(self.db_path):
            self._load()

    def _load(self) -> None:
        """Load index from file."""
        if not self.db_path:
            return
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
            f.flush()
            os.fsync(f.fileno())

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Tokenize text into lowercase words, filtering stop words."""
        if not text:
            return []
        words = re.findall(r"[a-z0-9]+", text.lower())
        return [w for w in words if w not in STOP_WORDS and len(w) > 1]

    def add_page(self, page: IndexedPage | CrawledPage) -> int:
        """Add a page to the index. Returns page id."""
        if isinstance(page, CrawledPage):
            from personal_index.url_utils import extract_domain
            crawled_at = getattr(page, "crawled_at", "")
            if hasattr(crawled_at, "isoformat"):
                crawled_at = crawled_at.isoformat()
            indexed = IndexedPage(
                url=page.url,
                title=page.title,
                content=page.content or "",
                score=getattr(page, "relevance_score", 0.0),
                crawled_at=crawled_at,
                domain=extract_domain(page.url) or "",
                status_code=getattr(page, "status_code", 200),
                content_length=len(page.content or ""),
                language=getattr(page, "language", "en"),
                keywords=getattr(page, "keywords", []),
                matched_interests=getattr(page, "matched_interests", []),
            )
        else:
            indexed = page
        self._pages[page.url] = indexed
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
        self._pages.pop(url)
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

    def list_pages(self) -> list[IndexedPage]:
        """List all pages sorted by score."""
        return sorted(self._pages.values(), key=lambda p: p.score, reverse=True)

    def clear(self) -> None:
        """Clear the index."""
        self._pages = {}
        self._word_index = {}
        self._save()

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search the index."""
        if not query:
            return []
        tokens = self._tokenize(query)
        if not tokens:
            return []

        scores: dict[str, float] = {}
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
        """Create a snippet highlighting the query terms."""
        if not content:
            return ""
        # Try to find each query token and create best snippet
        query_tokens = self._tokenize(query)
        best_idx = -1
        for token in query_tokens:
            idx = content.lower().find(token)
            if idx != -1:
                best_idx = idx
                break
        if best_idx == -1:
            return content[:length] + ("..." if len(content) > length else "")
        start = max(0, best_idx - 50)
        end = min(len(content), best_idx + length)
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
