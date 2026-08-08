"""Storage layer for personal-index."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from personal_index.models import CrawledPage, Interest


class StorageError(Exception):
    """Raised when storage operations fail."""
    pass


class InterestStore:
    """Persistent storage for user interests."""

    def __init__(self, data_dir: str = "~/.personal-index"):
        self.data_dir = Path(data_dir).expanduser()
        self.interests_file = self.data_dir / "interests.json"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create data directory if it doesn't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _load_interests(self) -> list[dict]:
        """Load interests from disk."""
        if self.interests_file.exists():
            with open(self.interests_file, "r") as f:
                return json.load(f)
        return []

    def _save_interests(self, interests: list[dict]) -> None:
        """Save interests to disk."""
        with open(self.interests_file, "w") as f:
            json.dump(interests, f, indent=2, default=str)

    def add_interest(self, interest: Interest) -> Interest:
        """Add a new interest."""
        interests = self._load_interests()
        # Check for duplicate topics
        for existing in interests:
            if existing["topic"] == interest.topic:
                raise ValueError(f"Interest with topic '{interest.topic}' already exists")
        interests.append({
            "topic": interest.topic,
            "keywords": interest.keywords,
            "url_patterns": interest.url_patterns,
            "created_at": interest.created_at.isoformat(),
            "enabled": interest.enabled,
        })
        self._save_interests(interests)
        return interest

    def get_interest(self, topic: str) -> Optional[Interest]:
        """Get an interest by topic."""
        interests = self._load_interests()
        for data in interests:
            if data["topic"] == topic:
                return Interest(
                    topic=data["topic"],
                    keywords=data["keywords"],
                    url_patterns=data["url_patterns"],
                    created_at=data["created_at"],
                    enabled=data["enabled"],
                )
        return None

    def list_interests(self, enabled_only: bool = False) -> list[Interest]:
        """List all interests."""
        interests = self._load_interests()
        result = []
        for data in interests:
            if enabled_only and not data["enabled"]:
                continue
            result.append(Interest(
                topic=data["topic"],
                keywords=data["keywords"],
                url_patterns=data["url_patterns"],
                created_at=data["created_at"],
                enabled=data["enabled"],
            ))
        return result

    def remove_interest(self, topic: str) -> bool:
        """Remove an interest by topic."""
        interests = self._load_interests()
        new_interests = [i for i in interests if i["topic"] != topic]
        if len(new_interests) == len(interests):
            return False
        self._save_interests(new_interests)
        return True

    def toggle_interest(self, topic: str) -> Optional[Interest]:
        """Toggle an interest's enabled status."""
        interests = self._load_interests()
        for data in interests:
            if data["topic"] == topic:
                data["enabled"] = not data["enabled"]
                self._save_interests(interests)
                return Interest(
                    topic=data["topic"],
                    keywords=data["keywords"],
                    url_patterns=data["url_patterns"],
                    created_at=data["created_at"],
                    enabled=data["enabled"],
                )
        return None


class PageStore:
    """Persistent storage for crawled pages."""

    def __init__(self, data_dir: str = "~/.personal-index"):
        self.data_dir = Path(data_dir).expanduser()
        self.pages_dir = self.data_dir / "pages"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create data directories if they don't exist."""
        self.pages_dir.mkdir(parents=True, exist_ok=True)

    def _page_file(self, page_id: str) -> Path:
        """Get the file path for a page."""
        return self.pages_dir / f"{page_id}.json"

    def save_page(self, page: CrawledPage) -> None:
        """Save a crawled page."""
        page_data = {
            "url": page.url,
            "title": page.title,
            "content": page.content,
            "meta_description": page.meta_description,
            "headers": page.headers,
            "status_code": page.status_code,
            "crawled_at": page.crawled_at.isoformat(),
            "depth": page.depth,
            "parent_url": page.parent_url,
            "matched_interests": page.matched_interests,
            "word_count": page.word_count,
        }
        with open(self._page_file(page.id), "w") as f:
            json.dump(page_data, f, indent=2)

    def get_page(self, page_id: str) -> Optional[CrawledPage]:
        """Get a page by ID."""
        page_file = self._page_file(page_id)
        if not page_file.exists():
            return None
        with open(page_file, "r") as f:
            data = json.load(f)
        return CrawledPage(
            url=data["url"],
            title=data["title"],
            content=data["content"],
            meta_description=data["meta_description"],
            headers=data["headers"],
            status_code=data["status_code"],
            crawled_at=data["crawled_at"],
            depth=data["depth"],
            parent_url=data["parent_url"],
            matched_interests=data["matched_interests"],
            word_count=data["word_count"],
        )

    def list_pages(self) -> list[CrawledPage]:
        """List all stored pages."""
        pages = []
        for page_file in self.pages_dir.glob("*.json"):
            with open(page_file, "r") as f:
                data = json.load(f)
            pages.append(CrawledPage(
                url=data["url"],
                title=data["title"],
                content=data["content"],
                meta_description=data["meta_description"],
                headers=data["headers"],
                status_code=data["status_code"],
                crawled_at=data["crawled_at"],
                depth=data["depth"],
                parent_url=data["parent_url"],
                matched_interests=data["matched_interests"],
                word_count=data["word_count"],
            ))
        return pages

    def delete_page(self, page_id: str) -> bool:
        """Delete a page by ID."""
        page_file = self._page_file(page_id)
        if page_file.exists():
            page_file.unlink()
            return True
        return False

    def count_pages(self) -> int:
        """Count stored pages."""
        return len(list(self.pages_dir.glob("*.json")))
