"""Interest store for managing user-defined interests."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from personal_index.models import Interest, InterestType


class InterestStore:
    """Persistent store for user interests."""

    def __init__(self, storage_path: str = "~/.personal-index/interests.json"):
        self._path = Path(storage_path).expanduser()
        self._interests: list[Interest] = []
        self._load()

    def _load(self) -> None:
        """Load interests from disk."""
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text())
                self._interests = [
                    Interest(
                        name=i["name"],
                        interest_type=InterestType(i["interest_type"]),
                        value=i["value"],
                        priority=i.get("priority", 5),
                        enabled=i.get("enabled", True),
                    )
                    for i in data
                ]
            except (json.JSONDecodeError, KeyError, ValueError):
                self._interests = []
        else:
            self._path.parent.mkdir(parents=True, exist_ok=True)

    def _save(self) -> None:
        """Save interests to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "name": i.name,
                "interest_type": i.interest_type.value,
                "value": i.value,
                "priority": i.priority,
                "enabled": i.enabled,
            }
            for i in self._interests
        ]
        self._path.write_text(json.dumps(data, indent=2))

    def add(self, interest: Interest) -> None:
        """Add a new interest."""
        self._interests.append(interest)
        self._save()

    def remove(self, name: str) -> bool:
        """Remove an interest by name. Returns True if found and removed."""
        before = len(self._interests)
        self._interests = [i for i in self._interests if i.name != name]
        if len(self._interests) < before:
            self._save()
            return True
        return False

    def get(self, name: str) -> Optional[Interest]:
        """Get an interest by name."""
        for interest in self._interests:
            if interest.name == name:
                return interest
        return None

    def list_all(self, enabled_only: bool = False) -> list[Interest]:
        """List all interests, optionally filtering to enabled only."""
        if enabled_only:
            return [i for i in self._interests if i.enabled]
        return list(self._interests)

    def toggle(self, name: str) -> Optional[Interest]:
        """Toggle an interest's enabled state."""
        interest = self.get(name)
        if interest:
            interest.enabled = not interest.enabled
            self._save()
        return interest

    def update_priority(self, name: str, priority: int) -> Optional[Interest]:
        """Update the priority of an interest."""
        interest = self.get(name)
        if interest:
            interest.priority = max(1, min(10, priority))
            self._save()
        return interest

    def matches_any(self, text: str, url: str = "") -> list[Interest]:
        """Return all interests that match the given text/url."""
        return [
            i for i in self._interests
            if i.enabled and i.matches(text, url)
        ]

    def total_score(self, text: str, url: str = "") -> float:
        """Calculate total relevance score across all interests."""
        return sum(i.score(text, url) for i in self._interests if i.enabled)
