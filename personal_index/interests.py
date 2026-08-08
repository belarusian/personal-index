"""
Interest management for personal-index.

Allows users to define topics, keywords, and URL patterns to track.
Interests are stored in a JSON file and used by the crawler and filter.
"""

import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
from datetime import datetime


@dataclass
class Interest:
    """A single interest to track."""
    name: str
    keywords: list[str] = field(default_factory=list)
    url_patterns: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    priority: int = 1  # 1-5, higher = more important
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    enabled: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Interest":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class InterestStore:
    """Manages the collection of user interests."""

    def __init__(self, store_path: Optional[str] = None):
        self.store_path = store_path
        self._interests: dict[str, Interest] = {}
        self._load()

    def _get_default_path(self) -> str:
        config_dir = Path.home() / ".config" / "personal-index"
        return str(config_dir / "interests.json")

    def _load(self) -> None:
        """Load interests from storage."""
        path = Path(self.store_path or self._get_default_path())
        if path.exists():
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                for name, interest_data in data.items():
                    self._interests[name] = Interest.from_dict(interest_data)
            except (json.JSONDecodeError, KeyError):
                self._interests = {}

    def _save(self) -> None:
        """Save interests to storage."""
        path = Path(self.store_path or self._get_default_path())
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump({name: i.to_dict() for name, i in self._interests.items()}, f, indent=2)

    def add(self, interest: Interest) -> None:
        """Add or update an interest."""
        self._interests[interest.name] = interest
        self._save()

    def remove(self, name: str) -> bool:
        """Remove an interest by name. Returns True if removed."""
        if name in self._interests:
            del self._interests[name]
            self._save()
            return True
        return False

    def get(self, name: str) -> Optional[Interest]:
        """Get an interest by name."""
        return self._interests.get(name)

    def list_all(self) -> list[Interest]:
        """List all interests."""
        return list(self._interests.values())

    def get_enabled(self) -> list[Interest]:
        """List all enabled interests."""
        return [i for i in self._interests.values() if i.enabled]

    def toggle(self, name: str) -> Optional[Interest]:
        """Toggle an interest's enabled state."""
        interest = self._interests.get(name)
        if interest:
            interest.enabled = not interest.enabled
            self._save()
        return interest

    def get_all_keywords(self) -> set[str]:
        """Get all keywords from enabled interests."""
        keywords = set()
        for interest in self.get_enabled():
            keywords.update(k.lower() for k in interest.keywords)
        return keywords

    def get_all_url_patterns(self) -> list[re.Pattern]:
        """Get compiled URL patterns from enabled interests."""
        patterns = []
        for interest in self.get_enabled():
            for pattern in interest.url_patterns:
                try:
                    patterns.append(re.compile(pattern, re.IGNORECASE))
                except re.error:
                    continue
        return patterns

    def get_all_topics(self) -> set[str]:
        """Get all topics from enabled interests."""
        topics = set()
        for interest in self.get_enabled():
            topics.update(t.lower() for t in interest.topics)
        return topics
