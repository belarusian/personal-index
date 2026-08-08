"""Persistent storage for crawled pages and crawl state."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class CrawlRecord:
    """Record of a crawl operation."""

    crawl_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    seed_urls: list[str] = None
    pages_crawled: int = 0
    pages_indexed: int = 0
    pages_failed: int = 0
    pages_filtered: int = 0
    error: Optional[str] = None

    def __post_init__(self) -> None:
        if self.seed_urls is None:
            self.seed_urls = []

    def to_dict(self) -> dict:
        return {
            "crawl_id": self.crawl_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "seed_urls": self.seed_urls,
            "pages_crawled": self.pages_crawled,
            "pages_indexed": self.pages_indexed,
            "pages_failed": self.pages_failed,
            "pages_filtered": self.pages_filtered,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> CrawlRecord:
        return cls(
            crawl_id=data["crawl_id"],
            started_at=datetime.fromisoformat(data["started_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            seed_urls=data.get("seed_urls", []),
            pages_crawled=data.get("pages_crawled", 0),
            pages_indexed=data.get("pages_indexed", 0),
            pages_failed=data.get("pages_failed", 0),
            pages_filtered=data.get("pages_filtered", 0),
            error=data.get("error"),
        )


class Storage:
    """SQLite-based storage for crawl records and page metadata."""

    def __init__(self, db_path: Path) -> None:
        """Initialize storage.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        cursor = self._conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS crawl_records (
                crawl_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                seed_urls TEXT NOT NULL,
                pages_crawled INTEGER DEFAULT 0,
                pages_indexed INTEGER DEFAULT 0,
                pages_failed INTEGER DEFAULT 0,
                pages_filtered INTEGER DEFAULT 0,
                error TEXT
            );

            CREATE TABLE IF NOT EXISTS page_metadata (
                page_id TEXT PRIMARY KEY,
                url TEXT NOT NULL UNIQUE,
                title TEXT,
                crawled_at TEXT,
                status_code INTEGER,
                content_length INTEGER,
                matched_interests TEXT,
                relevance_score REAL DEFAULT 0.0,
                last_updated TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_page_url ON page_metadata(url);
            CREATE INDEX IF NOT EXISTS idx_crawl_started ON crawl_records(started_at);
        """)
        self._conn.commit()

    def save_crawl_record(self, record: CrawlRecord) -> None:
        """Save a crawl record.

        Args:
            record: The crawl record to save.
        """
        cursor = self._conn.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO crawl_records
               (crawl_id, started_at, completed_at, seed_urls,
                pages_crawled, pages_indexed, pages_failed, pages_filtered, error)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.crawl_id,
                record.started_at.isoformat(),
                record.completed_at.isoformat() if record.completed_at else None,
                json.dumps(record.seed_urls),
                record.pages_crawled,
                record.pages_indexed,
                record.pages_failed,
                record.pages_filtered,
                record.error,
            ),
        )
        self._conn.commit()

    def get_crawl_records(self, limit: int = 50) -> list[CrawlRecord]:
        """Get recent crawl records.

        Args:
            limit: Maximum number of records to return.

        Returns:
            List of crawl records ordered by start time descending.
        """
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT * FROM crawl_records ORDER BY started_at DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()
        return [CrawlRecord.from_dict(dict(row)) for row in rows]

    def save_page_metadata(
        self,
        page_id: str,
        url: str,
        title: str,
        crawled_at: datetime,
        status_code: int,
        content_length: int,
        matched_interests: list[str],
        relevance_score: float,
    ) -> None:
        """Save page metadata.

        Args:
            page_id: Unique page identifier.
            url: Page URL.
            title: Page title.
            crawled_at: When the page was crawled.
            status_code: HTTP status code.
            content_length: Content length in bytes.
            matched_interests: List of matched interest topics.
            relevance_score: Relevance score.
        """
        cursor = self._conn.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO page_metadata
               (page_id, url, title, crawled_at, status_code,
                content_length, matched_interests, relevance_score, last_updated)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                page_id,
                url,
                title,
                crawled_at.isoformat(),
                status_code,
                content_length,
                json.dumps(matched_interests),
                relevance_score,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self._conn.commit()

    def get_page_metadata(self, url: str) -> Optional[dict]:
        """Get metadata for a page by URL.

        Args:
            url: The page URL.

        Returns:
            Page metadata dict, or None if not found.
        """
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM page_metadata WHERE url = ?", (url,))
        row = cursor.fetchone()
        if row:
            result = dict(row)
            result["matched_interests"] = json.loads(result["matched_interests"] or "[]")
            return result
        return None

    def get_total_pages(self) -> int:
        """Get total number of stored pages.

        Returns:
            Total page count.
        """
        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM page_metadata")
        return cursor.fetchone()["count"]

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def __enter__(self) -> Storage:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
