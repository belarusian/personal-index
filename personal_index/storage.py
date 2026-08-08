"""Page storage for crawled content."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class StoredPage:
    """A page stored on disk."""

    url: str
    title: str = ""
    content: str = ""
    file_hash: str = ""
    file_size: int = 0
    stored_at: str = ""

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "file_hash": self.file_hash,
            "file_size": self.file_size,
            "stored_at": self.stored_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StoredPage":
        return cls(**data)


@dataclass
class PageStore:
    """Stores crawled pages on disk."""

    store_dir: str
    _metadata: Dict[str, StoredPage] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        os.makedirs(self.store_dir, exist_ok=True)
        self._load_metadata()

    def _url_to_filename(self, url: str) -> str:
        """Convert URL to a safe filename."""
        hash_val = hashlib.md5(url.encode()).hexdigest()[:16]
        return f"{hash_val}.html"

    def _load_metadata(self) -> None:
        """Load metadata from disk."""
        meta_file = os.path.join(self.store_dir, "_metadata.json")
        if os.path.exists(meta_file):
            try:
                import json
                with open(meta_file, "r") as f:
                    data = json.load(f)
                self._metadata = {
                    url: StoredPage.from_dict(d) for url, d in data.items()
                }
            except (json.JSONDecodeError, KeyError):
                self._metadata = {}

    def _save_metadata(self) -> None:
        """Save metadata to disk."""
        import json
        meta_file = os.path.join(self.store_dir, "_metadata.json")
        data = {url: page.to_dict() for url, page in self._metadata.items()}
        with open(meta_file, "w") as f:
            json.dump(data, f, indent=2)

    def save_page(self, url: str, content: str, title: str = "") -> StoredPage:
        """Save a page to disk."""
        filename = self._url_to_filename(url)
        filepath = os.path.join(self.store_dir, filename)
        with open(filepath, "w") as f:
            f.write(content)
        file_hash = hashlib.md5(content.encode()).hexdigest()
        file_size = os.path.getsize(filepath)
        page = StoredPage(
            url=url,
            title=title,
            content=content,
            file_hash=file_hash,
            file_size=file_size,
            stored_at=datetime.utcnow().isoformat(),
        )
        self._metadata[url] = page
        self._save_metadata()
        return page

    def get_page(self, url: str) -> Optional[StoredPage]:
        """Get page metadata."""
        return self._metadata.get(url)

    def get_page_content(self, url: str) -> Optional[str]:
        """Get page content from disk."""
        if url not in self._metadata:
            return None
        filename = self._url_to_filename(url)
        filepath = os.path.join(self.store_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                return f.read()
        return None

    def delete_page(self, url: str) -> bool:
        """Delete a page from disk."""
        if url not in self._metadata:
            return False
        filename = self._url_to_filename(url)
        filepath = os.path.join(self.store_dir, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        del self._metadata[url]
        self._save_metadata()
        return True

    def list_pages(self) -> List[StoredPage]:
        """List all stored pages."""
        return list(self._metadata.values())

    def count_pages(self) -> int:
        """Count stored pages."""
        return len(self._metadata)

    def get_total_size(self) -> int:
        """Get total size of stored pages."""
        return sum(p.file_size for p in self._metadata.values())

    def clear(self) -> None:
        """Clear all stored pages."""
        for filename in os.listdir(self.store_dir):
            filepath = os.path.join(self.store_dir, filename)
            if os.path.isfile(filepath) and filename != "_metadata.json":
                os.remove(filepath)
        self._metadata = {}
        self._save_metadata()

    def has_page(self, url: str) -> bool:
        """Check if a page is stored."""
        return url in self._metadata

    def get_page_hash(self, url: str) -> Optional[str]:
        """Get the hash of a stored page."""
        page = self._metadata.get(url)
        return page.file_hash if page else None
