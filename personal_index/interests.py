"""Interest management module for CLI interface."""

from __future__ import annotations

import json
import os
import re
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Dict, List, Set

from personal_index.models import Interest


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
        if not self.store_path:
            return
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
                with suppress(re.error):
                    patterns.append(re.compile(pattern_str))
        return patterns

    def get_all_topics(self) -> Set[str]:
        """Get all topics from all interests (lowercase)."""
        topics = set()
        for interest in self._interests.values():
            for topic in interest.topics:
                topics.add(topic.lower())
        return topics

    def update_priority(self, name: str, priority: int) -> Interest | None:
        """Update an interest's priority (clamped 1-10)."""
        interest = self.get(name)
        if interest is None:
            return None
        interest.priority = max(1, min(10, priority))
        self._save()
        return interest

    def matches_any(self, text: str, url: str = "") -> List[Interest]:
        """Find all interests that match the given text/url."""
        matches = []
        for interest in self._interests.values():
            if interest.matches(text, url):
                matches.append(interest)
        return matches

    def total_score(self, text: str) -> float:
        """Calculate total relevance score across all interests."""
        return sum(interest.score(text) for interest in self._interests.values())
