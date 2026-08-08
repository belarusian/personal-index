"""Interest storage and management."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from personal_index.models import Interest, InterestType


def _serialize_interest(interest: Interest) -> dict:
    """Serialize an Interest to a JSON-safe dict."""
    d = asdict(interest)
    if isinstance(d.get("interest_type"), InterestType):
        d["interest_type"] = d["interest_type"].value
    if isinstance(d.get("created_at"), datetime):
        d["created_at"] = d["created_at"].isoformat()
    return d


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
            self._interests = []
            for i in data:
                interest_type = i.get("interest_type", "keyword")
                if isinstance(interest_type, str):
                    interest_type = InterestType(interest_type)
                created_at = i.get("created_at", "")
                if isinstance(created_at, str) and created_at:
                    try:
                        created_at = datetime.fromisoformat(created_at)
                    except ValueError:
                        created_at = datetime.utcnow()
                elif not isinstance(created_at, datetime):
                    created_at = datetime.utcnow()
                interest = Interest(
                    name=i["name"],
                    interest_type=interest_type,
                    value=i.get("value", ""),
                    keywords=i.get("keywords", []),
                    url_patterns=i.get("url_patterns", []),
                    topics=i.get("topics", []),
                    priority=i.get("priority", 5),
                    created_at=created_at,
                    enabled=i.get("enabled", True),
                )
                self._interests.append(interest)
        except (json.JSONDecodeError, KeyError, TypeError):
            self._interests = []

    def _save(self) -> None:
        """Save interests to storage file."""
        parent = Path(self.storage_path).parent
        parent.mkdir(parents=True, exist_ok=True)
        data = [_serialize_interest(i) for i in self._interests]
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
