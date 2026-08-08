"""
Local search index for personal-index.

Provides full-text search with relevance scoring using an inverted index
stored in SQLite.
"""

import sqlite3
import math
import re
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from pathlib import Path


@dataclass
class IndexedPage:
    """A page stored in the search index."""
    url: str
    title: str
    content: str
    keywords: list[str]
    score: float
    indexed_at: str
    source_interest: str = ""
    word_count: int = 0

    def to_dict(self) -> dict:
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


@dataclass
class SearchResult:
    """A single search result."""
    url: str
    title: str
    snippet: str
    relevance_score: float
    source_interest: str = ""
    indexed_at: str = ""

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "relevance_score": self.relevance_score,
            "source_interest": self.source_interest,
            "indexed_at": self.indexed_at,
        }


class SearchIndex:
    """Full-text search index backed by SQLite."""

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            data_dir = Path.home() / ".local" / "share" / "personal-index"
            db_path = str(data_dir / "index.db")
        self.db_path = db_path
        self._ensure_dirs()
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._init_schema()

    def _ensure_dirs(self) -> None:
        """Ensure the database directory exists."""
        path = Path(self.db_path)
        path.parent.mkdir(parents=True, exist_ok=True)

    def _init_schema(self) -> None:
        """Initialize the database schema."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL DEFAULT '',
                keywords TEXT NOT NULL DEFAULT '',
                score REAL NOT NULL DEFAULT 0.0,
                indexed_at TEXT NOT NULL,
                source_interest TEXT NOT NULL DEFAULT '',
                word_count INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS inverted_index (
                word TEXT NOT NULL,
                page_id INTEGER NOT NULL,
                frequency INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (word, page_id)
            );

            CREATE INDEX IF NOT EXISTS idx_word ON inverted_index(word);
            CREATE INDEX IF NOT EXISTS idx_page ON inverted_index(page_id);
            CREATE INDEX IF NOT EXISTS idx_score ON pages(score);
            CREATE INDEX IF NOT EXISTS idx_interest ON pages(source_interest);
        """)
        self._conn.commit()

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into lowercase words."""
        if not text:
            return []
        text = text.lower()
        words = re.findall(r'\b[a-z0-9]+\b', text)
        return [w for w in words if len(w) > 1]

    def _tf_idf_score(self, word: str, doc_freq: int, term_freq: int, total_docs: int) -> float:
        """Calculate TF-IDF score for a word."""
        if total_docs == 0:
            return 0.0
        tf = term_freq
        idf = math.log((1 + total_docs) / (1 + doc_freq)) + 1
        return tf * idf

    def add_page(self, page: IndexedPage) -> int:
        """Add or update a page in the index. Returns page id."""
        tokens = self._tokenize(page.content)
        word_freq: dict[str, int] = {}
        for token in tokens:
            word_freq[token] = word_freq.get(token, 0) + 1

        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT id FROM pages WHERE url = ?", (page.url,)
        )
        existing = cursor.fetchone()

        if existing:
            page_id = existing[0]
            cursor.execute(
                """UPDATE pages SET title = ?, content = ?, keywords = ?,
                   score = ?, indexed_at = ?, source_interest = ?, word_count = ?
                   WHERE id = ?""",
                (page.title, page.content, ",".join(page.keywords),
                 page.score, page.indexed_at, page.source_interest,
                 page.word_count, page_id)
            )
            cursor.execute("DELETE FROM inverted_index WHERE page_id = ?", (page_id,))
        else:
            cursor.execute(
                """INSERT INTO pages (url, title, content, keywords, score,
                   indexed_at, source_interest, word_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (page.url, page.title, page.content, ",".join(page.keywords),
                 page.score, page.indexed_at, page.source_interest,
                 page.word_count)
            )
            page_id = cursor.lastrowid

        for word, freq in word_freq.items():
            cursor.execute(
                "INSERT OR REPLACE INTO inverted_index (word, page_id, frequency) VALUES (?, ?, ?)",
                (word, page_id, freq)
            )

        self._conn.commit()
        return page_id

    def remove_page(self, url: str) -> bool:
        """Remove a page from the index."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT id FROM pages WHERE url = ?", (url,))
        row = cursor.fetchone()
        if row:
            page_id = row[0]
            cursor.execute("DELETE FROM inverted_index WHERE page_id = ?", (page_id,))
            cursor.execute("DELETE FROM pages WHERE id = ?", (page_id,))
            self._conn.commit()
            return True
        return False

    def search(self, query: str, limit: int = 20) -> list[SearchResult]:
        """Search the index for a query string."""
        tokens = self._tokenize(query)
        if not tokens:
            return []

        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM pages")
        total_docs = cursor.fetchone()[0]

        page_scores: dict[int, float] = {}

        for token in tokens:
            cursor.execute(
                """SELECT page_id, frequency FROM inverted_index WHERE word = ?""",
                (token,)
            )
            rows = cursor.fetchall()
            doc_freq = len(rows)

            for page_id, freq in rows:
                score = self._tf_idf_score(token, doc_freq, freq, total_docs)
                page_scores[page_id] = page_scores.get(page_id, 0) + score

        if not page_scores:
            return []

        page_ids = list(page_scores.keys())
        placeholders = ",".join("?" * len(page_ids))
        cursor.execute(
            f"""SELECT id, url, title, source_interest, indexed_at FROM pages
                WHERE id IN ({placeholders})""",
            page_ids
        )

        results = []
        for row in cursor.fetchall():
            page_id, url, title, source_interest, indexed_at = row
            relevance = page_scores[page_id]
            snippet = self._generate_snippet(title, url, query)
            results.append(SearchResult(
                url=url,
                title=title,
                snippet=snippet,
                relevance_score=relevance,
                source_interest=source_interest,
                indexed_at=indexed_at,
            ))

        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results[:limit]

    def _generate_snippet(self, title: str, url: str, query: str, max_length: int = 150) -> str:
        """Generate a snippet for a search result."""
        return title[:max_length]

    def get_page_count(self) -> int:
        """Get the total number of indexed pages."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM pages")
        return cursor.fetchone()[0]

    def get_page(self, url: str) -> Optional[IndexedPage]:
        """Get a page by URL."""
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT url, title, content, keywords, score, indexed_at, source_interest, word_count FROM pages WHERE url = ?",
            (url,)
        )
        row = cursor.fetchone()
        if row:
            return IndexedPage(
                url=row[0], title=row[1], content=row[2],
                keywords=row[3].split(",") if row[3] else [],
                score=row[4], indexed_at=row[5],
                source_interest=row[6], word_count=row[7]
            )
        return None

    def list_pages(self, limit: int = 50, offset: int = 0) -> list[IndexedPage]:
        """List indexed pages."""
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT url, title, content, keywords, score, indexed_at, source_interest, word_count FROM pages ORDER BY score DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        pages = []
        for row in cursor.fetchall():
            pages.append(IndexedPage(
                url=row[0], title=row[1], content=row[2],
                keywords=row[3].split(",") if row[3] else [],
                score=row[4], indexed_at=row[5],
                source_interest=row[6], word_count=row[7]
            ))
        return pages

    def clear(self) -> None:
        """Clear all indexed data."""
        self._conn.executescript("DELETE FROM inverted_index; DELETE FROM pages;")
        self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
