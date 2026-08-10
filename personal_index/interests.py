"""Interest management module for CLI interface."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Set


@dataclass
class Interest:
    """User interest for tracking topics."""

    name: str
    keywords: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    url_patterns: List[str] = field(default_factory=list)
    priority: int = 1
    enabled: bool = True

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "keywords": self.keywords,
            "topics": self.topics,
            "url_patterns": self.url_patterns,
            "priority": self.priority,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Interest":
        """Deserialize from dictionary."""
        return cls(
            name=data["name"],
            keywords=data.get("keywords", []),
            topics=data.get("topics", []),
            url_patterns=data.get("url_patterns", []),
            priority=data.get("priority", 1),
            enabled=data.get("enabled", True),
        )


@dataclass
class InterestStore:
    """Persistent storage for interests (CLI-facing)."""

    store_path: str | None = None
    _interests: Dict[str, Interest] = field(
        default_factory=dict, repr=False
    )

    def __post_init__(self):
        if self.store_path and os.path.exists(self.store_path):
            self._load()

    def _load(self) -> None:
        """Load interests from file."""
        try:
            with open(self.store_path, "r") as f:
                data = json.load(f)
            self._interests = {
                name: Interest.from_dict(d)
                for name, d in data.items()
            }
        except (json.JSONDecodeError, KeyError, TypeError):
            self._interests = {}

    def _save(self) -> None:
        """Save interests to file."""
        if not self.store_path:
            return
        os.makedirs(
            os.path.dirname(self.store_path) or ".", exist_ok=True
        )
        data = {
            name: interest.to_dict()
            for name, interest in self._interests.items()
        }
        with open(self.store_path, "w") as f:
            json.dump(data, f, indent=2)

    def add(self, interest: Interest) -> None:
        """Add an interest."""
        self._interests[interest.name] = interest
        self._save()

    def remove(self, name: str) -> bool:
        """Remove an interest by name."""
        if name in self._interests:
            del self._interests[name]
            self._save()
            return True
        return False

    def get(self, name: str) -> Interest | None:
        """Get an interest by name."""
        return self._interests.get(name)

    def list_all(self) -> List[Interest]:
        """List all interests."""
        return list(self._interests.values())

    def get_enabled(self) -> List[Interest]:
        """List enabled interests."""
        return [i for i in self._interests.values() if i.enabled]

    def toggle(self, name: str) -> Interest | None:
        """Toggle an interest's enabled status."""
        interest = self._interests.get(name)
        if interest is None:
            return None
        interest.enabled = not interest.enabled
        self._save()
        return interest

    def get_all_keywords(self) -> Set[str]:
        """Get all keywords from all interests (lowercase)."""
        keywords = set()
        for interest in self._interests.values():
            for kw in interest.keywords:
                keywords.add(kw.lower())
        return keywords

    def get_all_url_patterns(self) -> List[re.Pattern]:
        """Get all compiled URL patterns."""
        patterns = []
        for interest in self._interests.values():
            for pattern_str in interest.url_patterns:
                try:
                    patterns.append(re.compile(pattern_str))
                except re.error:
                    pass
        return patterns

    def get_all_topics(self) -> Set[str]:
        """Get all topics from all interests (lowercase)."""
        topics = set()
        for interest in self._interests.values():
            for topic in interest.topics:
                topics.add(topic.lower())
        return topics
