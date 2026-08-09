"""Content domain stats module - per-domain save statistics."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional
from urllib.parse import urlparse


@dataclass
class DomainStats:
    """Statistics for a single domain."""

    domain: str
    total_saves: int = 0
    unique_urls: int = 0
    total_size_bytes: int = 0
    top_tags: list[str] = field(default_factory=list)
    status_codes: dict[str, int] = field(default_factory=dict)
    avg_response_time_ms: float = 0.0
    _tracked_urls: set[str] = field(default_factory=set, repr=False)
    _response_times: list[float] = field(default_factory=list, repr=False)
    last_saved_at: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def record_save(
        self,
        size_bytes: int = 0,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        response_time_ms: Optional[float] = None,
        tags: Optional[list[str]] = None,
    ) -> None:
        """Record a save event for this domain."""
        self.total_saves += 1
        self.total_size_bytes += size_bytes
        self.last_saved_at = datetime.now(timezone.utc).isoformat()
        if url:
            self._tracked_urls.add(url)
            self.unique_urls = len(self._tracked_urls)
        if status_code:
            key = str(status_code)
            self.status_codes[key] = self.status_codes.get(key, 0) + 1
        if response_time_ms is not None:
            self._response_times.append(response_time_ms)
            self.avg_response_time_ms = (
                sum(self._response_times) / len(self._response_times)
            )
        if tags:
            for tag in tags:
                self.add_tag(tag)

    def add_url(self, url: str) -> None:
        """Add a tracked URL."""
        self._tracked_urls.add(url)
        self.unique_urls = len(self._tracked_urls)

    def add_tag(self, tag: str) -> None:
        """Add a tag to the top tags list."""
        if tag not in self.top_tags:
            self.top_tags.append(tag)

    def record_status_code(self, status_code: int) -> None:
        """Record a status code."""
        key = str(status_code)
        self.status_codes[key] = self.status_codes.get(key, 0) + 1

    def update_response_time(self, response_time_ms: float) -> None:
        """Update the average response time."""
        self._response_times.append(response_time_ms)
        self.avg_response_time_ms = (
            sum(self._response_times) / len(self._response_times)
        )

    def get_formatted_size(self) -> str:
        """Get human-readable size string."""
        size = self.total_size_bytes
        if size >= 1073741824:
            return f"{size / 1073741824:.2f} GB"
        elif size >= 1048576:
            return f"{size / 1048576:.2f} MB"
        elif size >= 1024:
            return f"{size / 1024:.2f} KB"
        else:
            return f"{size:.2f} B"

    def get_save_rate(self) -> float:
        """Get saves per day rate."""
        if self.total_saves == 0:
            return 0.0
        try:
            created = datetime.fromisoformat(self.created_at)
            now = datetime.now(timezone.utc)
            days = max((now - created).total_seconds() / 86400, 1)
            return round(self.total_saves / days, 2)
        except (ValueError, TypeError):
            return 0.0

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "domain": self.domain,
            "total_saves": self.total_saves,
            "unique_urls": self.unique_urls,
            "total_size_bytes": self.total_size_bytes,
            "top_tags": list(self.top_tags),
            "status_codes": dict(self.status_codes),
            "avg_response_time_ms": self.avg_response_time_ms,
            "last_saved_at": self.last_saved_at,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DomainStats":
        """Deserialize from dictionary."""
        created_at = data.get("created_at", datetime.now(timezone.utc).isoformat())
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()

        return cls(
            domain=data["domain"],
            total_saves=data.get("total_saves", 0),
            unique_urls=data.get("unique_urls", 0),
            total_size_bytes=data.get("total_size_bytes", 0),
            top_tags=data.get("top_tags", []),
            status_codes=data.get("status_codes", {}),
            avg_response_time_ms=data.get("avg_response_time_ms", 0.0),
            last_saved_at=data.get("last_saved_at"),
            created_at=created_at,
        )


class DomainStatsManager:
    """Manages per-domain save statistics."""

    def __init__(self) -> None:
        self._domains: dict[str, DomainStats] = {}
        self._save_history: dict[str, list[dict]] = {}

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            return parsed.hostname or ""
        except Exception:
            return ""

    def get_or_create_domain(self, domain: str) -> DomainStats:
        """Get or create domain stats."""
        if domain not in self._domains:
            self._domains[domain] = DomainStats(domain=domain)
            self._save_history[domain] = []
        return self._domains[domain]

    def record_save(
        self,
        url: str,
        size_bytes: int = 0,
        status_code: Optional[int] = None,
        response_time_ms: Optional[float] = None,
        tags: Optional[list[str]] = None,
    ) -> None:
        """Record a save event."""
        domain = self._extract_domain(url)
        if not domain:
            return
        ds = self.get_or_create_domain(domain)
        ds.record_save(
            size_bytes=size_bytes,
            url=url,
            status_code=status_code,
            response_time_ms=response_time_ms,
            tags=tags,
        )
        self._save_history.setdefault(domain, []).append({
            "url": url,
            "size_bytes": size_bytes,
            "status_code": status_code,
            "response_time_ms": response_time_ms,
            "tags": tags or [],
            "saved_at": datetime.now(timezone.utc).isoformat(),
        })

    def get_domain_stats(self, domain: str) -> Optional[DomainStats]:
        """Get stats for a domain."""
        return self._domains.get(domain)

    def list_domains(self, sort_by: str = "saves") -> list[DomainStats]:
        """List all domain stats, optionally sorted."""
        domains = list(self._domains.values())
        if sort_by == "saves":
            domains.sort(key=lambda d: d.total_saves, reverse=True)
        elif sort_by == "size":
            domains.sort(key=lambda d: d.total_size_bytes, reverse=True)
        elif sort_by == "name":
            domains.sort(key=lambda d: d.domain)
        return domains

    def get_domain_count(self) -> int:
        """Get total number of tracked domains."""
        return len(self._domains)

    def get_total_saves(self) -> int:
        """Get total saves across all domains."""
        return sum(d.total_saves for d in self._domains.values())

    def get_total_size(self) -> int:
        """Get total size across all domains."""
        return sum(d.total_size_bytes for d in self._domains.values())

    def get_top_domains(self, limit: int = 10) -> list[DomainStats]:
        """Get top domains by save count."""
        return self.list_domains(sort_by="saves")[:limit]

    def get_domain_summary(self) -> dict:
        """Get a summary of all domain stats."""
        return {
            "total_domains": len(self._domains),
            "total_saves": self.get_total_saves(),
            "total_size_bytes": self.get_total_size(),
            "total_size_formatted": self._format_size(self.get_total_size()),
        }

    def remove_domain(self, domain: str) -> bool:
        """Remove a domain's stats. Returns True if removed."""
        if domain in self._domains:
            del self._domains[domain]
            self._save_history.pop(domain, None)
            return True
        return False

    def reset_domain(self, domain: str) -> None:
        """Reset a domain's stats to zero."""
        ds = self._domains.get(domain)
        if ds:
            ds.total_saves = 0
            ds.unique_urls = 0
            ds.total_size_bytes = 0
            ds.top_tags = []
            ds.status_codes = {}
            ds.avg_response_time_ms = 0.0
            ds._tracked_urls = set()
            ds._response_times = []
            self._save_history[domain] = []

    def get_domains_by_tag(self, tag: str) -> list[DomainStats]:
        """Get domains that have a specific tag."""
        return [d for d in self._domains.values() if tag in d.top_tags]

    def get_save_history(self, domain: str, limit: int = 50) -> list[dict]:
        """Get save history for a domain."""
        history = self._save_history.get(domain, [])
        return history[-limit:]

    def get_domains_with_errors(self) -> list[DomainStats]:
        """Get domains that have error status codes."""
        return [
            d for d in self._domains.values()
            if any(int(code) >= 400 for code in d.status_codes)
        ]

    def get_domain_percentage(self, domain: str) -> float:
        """Get the percentage of total saves for a domain."""
        total = self.get_total_saves()
        if total == 0:
            return 0.0
        ds = self._domains.get(domain)
        if not ds:
            return 0.0
        return round((ds.total_saves / total) * 100, 2)

    def _format_size(self, size_bytes: int) -> str:
        """Format bytes to human-readable string."""
        if size_bytes >= 1073741824:
            return f"{size_bytes / 1073741824:.2f} GB"
        elif size_bytes >= 1048576:
            return f"{size_bytes / 1048576:.2f} MB"
        elif size_bytes >= 1024:
            return f"{size_bytes / 1024:.2f} KB"
        else:
            return f"{size_bytes} B"

    def to_dict(self) -> dict:
        """Serialize the manager state."""
        return {
            "domains": {
                d: ds.to_dict() for d, ds in self._domains.items()
            },
            "save_history": dict(self._save_history),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DomainStatsManager":
        """Deserialize manager state."""
        mgr = cls()
        for domain, ddata in data.get("domains", {}).items():
            ds = DomainStats.from_dict(ddata)
            mgr._domains[domain] = ds
        mgr._save_history = data.get("save_history", {})
        return mgr
