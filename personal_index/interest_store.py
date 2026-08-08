"""Interest storage and management."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from personal_index.models import Interest, InterestType


@dataclass
class InterestStore:
    """Persistent storage for user interests."""

    storage_path: str
    _interests: List[Interest] = field(default_factory=list, repr=False)

    def __post_init__(self):
        self._load()

    def _load(self) -> None:
        """Load interests from storage file."""
        if not os.path.exists(self.storage_path):
            self._interests = []
            return
        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
            self._interests = [
                Interest(
                    name=i["name"],
                    interest_type=InterestType(i["interest_type"]),
                    value=i["value"],
                    priority=i["priority"],
                    enabled=i.get("enabled", True),
                    created_at=datetime.fromisoformat(i["created_at"])
                    if "created_at" in i
                    else datetime.utcnow(),
                )
                for i in data
            ]
        except (json.JSONDecodeError, KeyError, TypeError):
            self._interests = []

    def _save(self) -> None:
        """Save interests to storage file."""
        parent = Path(self.storage_path).parent
        parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(i) for i in self._interests]
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def add(self, interest: Interest) -> None:
        """Add an interest to the store."""
        self._interests.append(interest)
        self._save()

    def remove(self, name: str) -> bool:
        """Remove an interest by name. Returns True if found and removed."""
        for i, interest in enumerate(self._interests):
            if interest.name == name:
                self._interests.pop(i)
                self._save()
                return True
        return False

    def get(self, name: str) -> Optional[Interest]:
        """Get an interest by name."""
        for interest in self._interests:
            if interest.name == name:
                return interest
        return None

    def list_all(self, enabled_only: bool = False) -> List[Interest]:
        """List all interests, optionally filtering by enabled status."""
        if enabled_only:
            return [i for i in self._interests if i.enabled]
        return list(self._interests)

    def toggle(self, name: str) -> Optional[Interest]:
        """Toggle an interest's enabled status."""
        interest = self.get(name)
        if interest is None:
            return None
        interest.enabled = not interest.enabled
        self._save()
        return interest

    def update_priority(self, name: str, priority: int) -> Optional[Interest]:
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
        for interest in self._interests:
            if interest.matches(text, url):
                matches.append(interest)
        return matches

    def total_score(self, text: str) -> float:
        """Calculate total relevance score across all interests."""
        return sum(interest.score(text) for interest in self._interests)
