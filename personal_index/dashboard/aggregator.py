"""Data aggregation for the admin dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TimeSeriesPoint:
    """A single point in a time series."""
    timestamp: str
    value: float
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "value": self.value,
            "label": self.label,
        }


@dataclass
class AggregatedStats:
    """Aggregated statistics for the dashboard."""
    total_pages: int = 0
    total_domains: int = 0
    total_interests: int = 0
    total_keywords: int = 0
    avg_relevance_score: float = 0.0
    pages_per_day: float = 0.0
    crawl_success_rate: float = 100.0
    top_domains: list[dict[str, Any]] = field(default_factory=list)
    recent_activity: list[TimeSeriesPoint] = field(default_factory=list)
    status_breakdown: dict[str, int] = field(default_factory=dict)
    content_type_breakdown: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_pages": self.total_pages,
            "total_domains": self.total_domains,
            "total_interests": self.total_interests,
            "total_keywords": self.total_keywords,
            "avg_relevance_score": round(self.avg_relevance_score, 2),
            "pages_per_day": round(self.pages_per_day, 1),
            "crawl_success_rate": round(self.crawl_success_rate, 1),
            "top_domains": self.top_domains,
            "recent_activity": [p.to_dict() for p in self.recent_activity],
            "status_breakdown": self.status_breakdown,
            "content_type_breakdown": self.content_type_breakdown,
        }


class DashboardAggregator:
    """Aggregates data from index instances for dashboard display."""

    def __init__(self):
        self._cached_stats: AggregatedStats | None = None
        self._cache_time: float = 0.0
        self._cache_ttl: float = 30.0  # 30 second cache

    def _compute_avg_relevance(self, pages: list) -> float:
        scores = [p.relevance_score for p in pages if hasattr(p, "relevance_score")]
        return sum(scores) / len(scores) if scores else 0.0

    def _compute_total_domains(self, pages: list) -> int:
        domains = {p.domain for p in pages if hasattr(p, "domain") and p.domain}
        return len(domains)

    def _compute_total_keywords(self, pages: list) -> int:
        keywords: set = set()
        for p in pages:
            if hasattr(p, "keywords") and p.keywords:
                keywords.update(p.keywords)
        return len(keywords)

    def _compute_pages_per_day(self, pages: list) -> float:
        if len(pages) < 2:
            return 0.0
        dates = []
        for p in pages:
            if hasattr(p, "crawled_at") and p.crawled_at:
                try:
                    dates.append(
                        datetime.fromisoformat(p.crawled_at) if isinstance(p.crawled_at, str) else p.crawled_at
                    )
                except (ValueError, TypeError):
                    pass
        if len(dates) < 2:
            return 0.0
        span = (max(dates) - min(dates)).total_seconds()
        if span > 0:
            return len(pages) / max(span / 86400, 1)
        return 0.0

    def _compute_success_rate(self, pages: list) -> float:
        if not pages:
            return 100.0
        success = sum(1 for p in pages if hasattr(p, "status_code") and 200 <= (p.status_code or 0) < 300)
        return success / len(pages) * 100

    def _apply_page_stats(self, stats: AggregatedStats, pages: list) -> None:
        if not pages:
            return
        stats.avg_relevance_score = self._compute_avg_relevance(pages)
        stats.total_domains = self._compute_total_domains(pages)
        stats.total_keywords = self._compute_total_keywords(pages)
        stats.pages_per_day = self._compute_pages_per_day(pages)
        stats.crawl_success_rate = self._compute_success_rate(pages)

    def aggregate(
        self,
        index_instance=None,
        search_index=None,
        config=None,
        force_refresh: bool = False,
    ) -> AggregatedStats:
        """Aggregate statistics from available data sources."""
        import time
        now = time.time()
        if not force_refresh and self._cached_stats and (now - self._cache_time) < self._cache_ttl:
            return self._cached_stats

        stats = AggregatedStats()

        if index_instance:
            pages = self._get_pages(index_instance)
            stats.total_pages = len(pages)
            stats.top_domains = self._compute_top_domains(pages)
            stats.status_breakdown = self._compute_status_breakdown(pages)
            stats.content_type_breakdown = self._compute_content_types(pages)
            stats.recent_activity = self._compute_recent_activity(pages)
            self._apply_page_stats(stats, pages)

        if index_instance and hasattr(index_instance, "interests"):
            stats.total_interests = len(index_instance.interests)

        self._cached_stats = stats
        self._cache_time = now
        return stats

    def _get_pages(self, index_instance) -> list:
        """Get pages from index instance."""
        if hasattr(index_instance, "get_all_pages"):
            return index_instance.get_all_pages()  # type: ignore[no-any-return]
        if hasattr(index_instance, "pages"):
            return list(index_instance.pages)
        return []

    def _compute_top_domains(self, pages: list, limit: int = 10) -> list[dict[str, Any]]:
        """Compute top domains by page count."""
        domain_counts: dict[str, int] = {}
        for p in pages:
            domain = getattr(p, "domain", None)
            if domain:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
        sorted_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)
        return [
            {"domain": d, "count": c, "percentage": round(c / len(pages) * 100, 1) if pages else 0}
            for d, c in sorted_domains[:limit]
        ]

    def _compute_status_breakdown(self, pages: list) -> dict[str, int]:
        """Compute HTTP status code breakdown."""
        breakdown: dict[str, int] = {}
        for p in pages:
            code = getattr(p, "status_code", 0)
            category = f"{code // 100}xx" if code else "unknown"
            breakdown[category] = breakdown.get(category, 0) + 1
        return breakdown

    def _compute_content_types(self, pages: list) -> dict[str, int]:
        """Compute content type breakdown."""
        breakdown: dict[str, int] = {}
        for p in pages:
            content_type = getattr(p, "content_type", None) or "unknown"
            breakdown[content_type] = breakdown.get(content_type, 0) + 1
        return breakdown

    def _compute_recent_activity(self, pages: list, limit: int = 24) -> list[TimeSeriesPoint]:
        """Compute recent crawl activity as time series."""
        if not pages:
            return []
        dates: dict[str, int] = {}
        for p in pages:
            crawled_at = getattr(p, "crawled_at", None)
            if crawled_at:
                try:
                    if isinstance(crawled_at, str):
                        dt = datetime.fromisoformat(crawled_at)
                    else:
                        dt = crawled_at
                    day_key = dt.strftime("%Y-%m-%d")
                    dates[day_key] = dates.get(day_key, 0) + 1
                except (ValueError, TypeError):
                    pass
        sorted_dates = sorted(dates.items(), reverse=True)[:limit]
        return [
            TimeSeriesPoint(timestamp=day, value=count, label=day)
            for day, count in sorted_dates
        ]

    def clear_cache(self) -> None:
        """Clear the stats cache."""
        self._cached_stats = None
        self._cache_time = 0.0
