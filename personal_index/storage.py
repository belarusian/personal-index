"""
Storage management for personal-index.

Handles file-based storage for crawled pages, cache, and metadata.
"""

import hashlib
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class StoredPage:
    """A page stored on disk."""
    url: str
    title: str
    content: str
    content_type: str = "text/html"
    status_code: int = 200
    crawled_at: str = ""
    file_hash: str = ""
    file_size: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "StoredPage":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class PageStore:
    """File-based storage for crawled pages."""

    def __init__(self, store_dir: Optional[str] = None):
        if store_dir is None:
            store_dir = str(Path.home() / ".local" / "share" / "personal-index" / "pages")
        self.store_dir = store_dir
        self._metadata_path = os.path.join(store_dir, "metadata.json")
        self._pages: dict[str, StoredPage] = {}
        self._ensure_dir()
        self._load_metadata()

    def _ensure_dir(self) -> None:
        """Ensure the store directory exists."""
        Path(self.store_dir).mkdir(parents=True, exist_ok=True)

    def _url_to_filename(self, url: str) -> str:
        """Convert a URL to a safe filename."""
        hash_input = url.encode("utf-8")
        file_hash = hashlib.sha256(hash_input).hexdigest()[:16]
        return f"{file_hash}.html"

    def _load_metadata(self) -> None:
        """Load page metadata from file."""
        if os.path.exists(self._metadata_path):
            try:
                with open(self._metadata_path, "r") as f:
                    data = json.load(f)
                for url, page_data in data.items():
                    self._pages[url] = StoredPage.from_dict(page_data)
            except (json.JSONDecodeError, KeyError):
                self._pages = {}

    def _save_metadata(self) -> None:
        """Save page metadata to file."""
        with open(self._metadata_path, "w") as f:
            json.dump({url: p.to_dict() for url, p in self._pages.items()}, f, indent=2)

    def save_page(self, url: str, content: str, title: str = "",
                  content_type: str = "text/html", status_code: int = 200) -> StoredPage:
        """Save a page to disk."""
        filename = self._url_to_filename(url)
        filepath = os.path.join(self.store_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        file_size = os.path.getsize(filepath)

        page = StoredPage(
            url=url,
            title=title,
            content="",  # Don't store full content in metadata
            content_type=content_type,
            status_code=status_code,
            crawled_at=datetime.utcnow().isoformat(),
            file_hash=file_hash,
            file_size=file_size,
        )
        self._pages[url] = page
        self._save_metadata()
        return page

    def get_page(self, url: str) -> Optional[StoredPage]:
        """Get metadata for a stored page."""
        return self._pages.get(url)

    def get_page_content(self, url: str) -> Optional[str]:
        """Get the raw content of a stored page."""
        filename = self._url_to_filename(url)
        filepath = os.path.join(self.store_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def delete_page(self, url: str) -> bool:
        """Delete a stored page."""
        filename = self._url_to_filename(url)
        filepath = os.path.join(self.store_dir, filename)

        if os.path.exists(filepath):
            os.remove(filepath)

        if url in self._pages:
            del self._pages[url]
            self._save_metadata()
            return True
        return False

    def list_pages(self) -> list[StoredPage]:
        """List all stored pages."""
        return list(self._pages.values())

    def count_pages(self) -> int:
        """Count stored pages."""
        return len(self._pages)

    def get_total_size(self) -> int:
        """Get total storage size in bytes."""
        total = 0
        for page in self._pages.values():
            total += page.file_size
        return total

    def clear(self) -> None:
        """Clear all stored pages."""
        for page in self._pages.values():
            filename = self._url_to_filename(page.url)
            filepath = os.path.join(self.store_dir, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
        self._pages.clear()
        self._save_metadata()

    def has_page(self, url: str) -> bool:
        """Check if a page is stored."""
        return url in self._pages

    def get_page_hash(self, url: str) -> Optional[str]:
        """Get the content hash of a stored page."""
        page = self._pages.get(url)
        if page:
            return page.file_hash
        return None
