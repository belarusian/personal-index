"""URL history tracking for crawled and visited pages."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse


@dataclass
class URLVisit:
    """Record of a single URL visit."""
    url: str
    timestamp: str = ""
    status_code: int = 0
    content_length: int = 0
    title: str = ""
    user_agent: str = ""
    response_time_ms: float = 0.0
    error: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """To_dict."""
        return {
            "url": self.url,
            "timestamp": self.timestamp,
            "status_code": self.status_code,
            "content_length": self.content_length,
            "title": self.title,
            "user_agent": self.user_agent,
            "response_time_ms": self.response_time_ms,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> URLVisit:
        """Process from_dict.

        Args:
        data.
        """
        return cls(**data)


class URLHistory:
    """Track URL visit history with persistence."""

    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries
        self._history: List[URLVisit] = []

    def record(self, url: str, status_code: int = 200,
               content_length: int = 0, title: str = "",
               user_agent: str = "", response_time_ms: float = 0.0,
               error: str = "") -> URLVisit:
        """Record a URL visit."""
        visit = URLVisit(
            url=url,
            status_code=status_code,
            content_length=content_length,
            title=title,
            user_agent=user_agent,
            response_time_ms=response_time_ms,
            error=error,
        )
        self._history.append(visit)
        self._trim()
        return visit

    def get_visits(self, url: str | None = None,
                   since: str | None = None,
                   limit: int = 100) -> List[URLVisit]:
        """Get visit records, optionally filtered by URL and time."""
        results = self._history
        if url:
            results = [v for v in results if v.url == url]
        if since:
            results = [v for v in results if v.timestamp >= since]
        return results[-limit:]

    def get_unique_urls(self) -> List[str]:
        """Get list of unique URLs visited."""
        seen = set()
        urls = []
        for v in reversed(self._history):
            if v.url not in seen:
                seen.add(v.url)
                urls.append(v.url)
        return urls

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about URL history."""
        if not self._history:
            return {
                "total_visits": 0,
                "unique_urls": 0,
                "avg_response_time_ms": 0.0,
                "error_count": 0,
                "success_count": 0,
            }

        total = len(self._history)
        unique = len(set(v.url for v in self._history))
        errors = sum(1 for v in self._history if v.status_code >= 400 or v.error)
        successes = total - errors
        response_times = [v.response_time_ms for v in self._history if v.response_time_ms > 0]
        avg_response = sum(response_times) / len(response_times) if response_times else 0.0

        return {
            "total_visits": total,
            "unique_urls": unique,
            "avg_response_time_ms": round(avg_response, 2),
            "error_count": errors,
            "success_count": successes,
        }

    def get_domain_stats(self) -> Dict[str, Dict[str, int]]:
        """Get visit counts grouped by domain."""
        domains: Dict[str, Dict[str, int]] = {}
        for v in self._history:
            try:
                domain = urlparse(v.url).netloc or "unknown"
            except Exception:
                domain = "unknown"
            if domain not in domains:
                domains[domain] = {"visits": 0, "errors": 0}
            domains[domain]["visits"] += 1
            if v.status_code >= 400 or v.error:
                domains[domain]["errors"] += 1
        return domains

    def clear(self) -> int:
        """Clear all history. Returns count of cleared entries."""
        count = len(self._history)
        self._history.clear()
        return count

    def save(self, filepath: str) -> None:
        """Save history to file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [v.to_dict() for v in self._history]
        with open(str(path), "w") as f:
            json.dump(data, f, indent=2)

    def load(self, filepath: str) -> int:
        """Load history from file. Returns count loaded."""
        path = Path(filepath)
        if not path.exists():
            return 0
        with open(str(path)) as f:
            data = json.load(f)
        self._history = [URLVisit.from_dict(d) for d in data]
        self._trim()
        return len(self._history)

    def _trim(self) -> None:
        """Trim history to max entries."""
        if len(self._history) > self.max_entries:
            self._history = self._history[-self.max_entries:]
