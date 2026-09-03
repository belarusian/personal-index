"""Storage layer for personal-index using JSON files."""

import json
from pathlib import Path

from personal_index.models import CrawlConfig, IndexedPage, Interest


class Storage:
    """File-based storage for interests, config, and indexed pages."""

    def __init__(self, data_dir: str = ".personal-index"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.interests_file = self.data_dir / "interests.json"
        self.config_file = self.data_dir / "config.json"
        self.pages_file = self.data_dir / "pages.json"
        self._ensure_files()

    def _ensure_files(self):
        """Create empty JSON files if they don't exist."""
        if not self.interests_file.exists():
            self.interests_file.write_text("[]")
        if not self.config_file.exists():
            self.config_file.write_text("{}")
        if not self.pages_file.exists():
            self.pages_file.write_text("[]")

    def _read_json(self, filepath: Path) -> list | dict:
        default: list | dict = (
            [] if filepath.name in ("interests.json", "pages.json") else {}
        )
        content = filepath.read_text()
        if not content.strip():
            return default
        try:
            return json.loads(content)  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            return default

    def _write_json(self, filepath: Path, data):
        filepath.write_text(json.dumps(data, indent=2, default=str))

    # --- Interests ---

    def add_interest(self, interest: Interest) -> Interest:
        """Add a new interest."""
        interests = self._read_json(self.interests_file)
        if not isinstance(interests, list):
            interests = []
        for i, existing in enumerate(interests):
            if existing["name"] == interest.name:
                interests[i] = interest.to_dict()
                self._write_json(self.interests_file, interests)
                return interest
        interests.append(interest.to_dict())
        self._write_json(self.interests_file, interests)
        return interest

    def get_interests(self) -> list[Interest]:
        """Get all interests."""
        data = self._read_json(self.interests_file)
        if not isinstance(data, list):
            return []
        return [Interest.from_dict(item) for item in data]

    def get_interest(self, name: str) -> Interest | None:
        """Get a single interest by name."""
        for interest in self.get_interests():
            if interest.name == name:
                return interest
        return None

    def remove_interest(self, name: str) -> bool:
        """Remove an interest by name."""
        interests = self._read_json(self.interests_file)
        original_len = len(interests)
        interests = [i for i in interests if i["name"] != name]
        if len(interests) < original_len:
            self._write_json(self.interests_file, interests)
            return True
        return False

    def list_interests(self) -> list[dict]:
        """List all interests with summary info."""
        results = []
        for interest in self.get_interests():
            results.append({
                "name": interest.name,
                "keywords": interest.keywords,
                "url_patterns": interest.url_patterns,
                "topics": interest.topics,
                "enabled": interest.enabled,
                "created_at": interest.created_at,
            })
        return results

    # --- Crawl Config ---

    def save_config(self, config: CrawlConfig) -> CrawlConfig:
        """Save crawl configuration."""
        self._write_json(self.config_file, config.to_dict())
        return config

    def get_config(self) -> CrawlConfig:
        """Get crawl configuration."""
        data = self._read_json(self.config_file)
        if not data or not isinstance(data, dict):
            return CrawlConfig()
        return CrawlConfig.from_dict(data)

    # --- Indexed Pages ---

    def add_page(self, page: IndexedPage) -> IndexedPage:
        """Add or update an indexed page."""
        pages = self._read_json(self.pages_file)
        if not isinstance(pages, list):
            pages = []
        for i, existing in enumerate(pages):
            if existing["url"] == page.url:
                pages[i] = page.to_dict()
                self._write_json(self.pages_file, pages)
                return page
        pages.append(page.to_dict())
        self._write_json(self.pages_file, pages)
        return page

    def get_pages(self) -> list[IndexedPage]:
        """Get all indexed pages."""
        data = self._read_json(self.pages_file)
        if not isinstance(data, list):
            return []
        return [IndexedPage.from_dict(item) for item in data]

    def get_page(self, url: str) -> IndexedPage | None:
        """Get a single page by URL."""
        for page in self.get_pages():
            if page.url == url:
                return page
        return None

    def remove_page(self, url: str) -> bool:
        """Remove a page by URL."""
        pages = self._read_json(self.pages_file)
        original_len = len(pages)
        pages = [p for p in pages if p["url"] != url]
        if len(pages) < original_len:
            self._write_json(self.pages_file, pages)
            return True
        return False

    def get_page_count(self) -> int:
        """Get total number of indexed pages."""
        return len(self._read_json(self.pages_file))

    def clear_pages(self):
        """Clear all indexed pages."""
        self._write_json(self.pages_file, [])

    def get_stats(self) -> dict:
        """Get storage statistics."""
        interests = self.get_interests()
        pages = self.get_pages()
        return {
            "total_interests": len(interests),
            "enabled_interests": sum(
                1 for i in interests if i.enabled
            ),
            "total_pages": len(pages),
            "total_content_bytes": sum(
                p.content_length for p in pages
            ),
            "data_dir": str(self.data_dir),
        }
