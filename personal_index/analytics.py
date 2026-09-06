"""Analytics module for personal index usage tracking."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class SearchEvent:
    """A search event record."""
    query: str
    timestamp: str = ""
    result_count: int = 0
    clicked_url: str | None = None
    duration_ms: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class CrawlEvent:
    """A crawl event record."""
    url: str
    timestamp: str = ""
    status_code: int = 0
    content_size: int = 0
    duration_ms: float = 0.0
    error: str | None = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class AnalyticsData:
    """Aggregated analytics data."""
    total_searches: int = 0
    total_crawls: int = 0
    total_pages_indexed: int = 0
    avg_search_duration_ms: float = 0.0
    avg_crawl_duration_ms: float = 0.0
    top_queries: list[tuple[str, int]] = field(default_factory=list)
    top_domains: list[tuple[str, int]] = field(default_factory=list)
    hourly_searches: dict[str, int] = field(default_factory=dict)
    daily_searches: dict[str, int] = field(default_factory=dict)
    error_count: int = 0
    success_count: int = 0


class AnalyticsTracker:
    """Track and analyze personal index usage."""

    def __init__(self):
        self._search_events: list[SearchEvent] = []
        self._crawl_events: list[CrawlEvent] = []

    def record_search(self, query: str | SearchEvent, result_count: int = 0,
                      clicked_url: str | None = None,
                      duration_ms: float = 0.0) -> SearchEvent:
        """Record a search event.

        Args:
            query: Either a search query string or a SearchEvent object.
            result_count: Number of results (ignored if SearchEvent is passed).
            clicked_url: URL that was clicked (ignored if SearchEvent is passed).
            duration_ms: Duration in ms (ignored if SearchEvent is passed).
        """
        if isinstance(query, SearchEvent):
            event = query
        else:
            event = SearchEvent(
                query=query,
                result_count=result_count,
                clicked_url=clicked_url,
                duration_ms=duration_ms,
            )
        self._search_events.append(event)
        return event

    def record_crawl(self, url: str, status_code: int = 200,
                     content_size: int = 0, duration_ms: float = 0.0,
                     error: str | None = None) -> CrawlEvent:
        """Record a crawl event.

        Constructs a CrawlEvent from the given fields, appends it to the
        internal crawl event list (``self._crawl_events``), and returns the
        constructed event.

        Args:
            url: The URL that was crawled (required).
            status_code: HTTP status code (default 200).
            content_size: Content size in bytes (default 0).
            duration_ms: Duration in ms (default 0.0).
            error: Error message if the crawl failed (default None).

        Returns:
            The constructed CrawlEvent (its timestamp is auto-set by the
            dataclass when not provided).
        """
        event = CrawlEvent(
            url=url,
            status_code=status_code,
            content_size=content_size,
            duration_ms=duration_ms,
            error=error,
        )
        self._crawl_events.append(event)
        return event

    def _compute_search_analytics(self, top_n: int) -> AnalyticsData:
        """Compute search-related analytics metrics.

        Args:
            top_n: Number of top queries to return.

        Returns:
            AnalyticsData with search-related fields populated.
        """
        data = AnalyticsData()
        data.total_searches = len(self._search_events)

        if self._search_events:
            durations = [e.duration_ms for e in self._search_events if e.duration_ms > 0]
            if durations:
                data.avg_search_duration_ms = sum(durations) / len(durations)

            # Top queries
            query_counter = Counter(e.query for e in self._search_events)
            data.top_queries = query_counter.most_common(top_n)

            # Hourly distribution
            hourly: Counter[str] = Counter()
            daily: Counter[str] = Counter()
            for e in self._search_events:
                try:
                    dt = datetime.fromisoformat(e.timestamp)
                    hourly[dt.strftime("%H:00")] += 1
                    daily[dt.strftime("%Y-%m-%d")] += 1
                except (ValueError, TypeError):
                    pass
            data.hourly_searches = dict(hourly)
            data.daily_searches = dict(daily)

        return data

    def _compute_crawl_analytics(self, top_n: int) -> AnalyticsData:
        """Compute crawl-related analytics metrics.

        Args:
            top_n: Number of top domains to return.

        Returns:
            AnalyticsData with crawl-related fields populated.
        """
        data = AnalyticsData()
        data.total_crawls = len(self._crawl_events)

        if self._crawl_events:
            durations = [e.duration_ms for e in self._crawl_events if e.duration_ms > 0]
            if durations:
                data.avg_crawl_duration_ms = sum(durations) / len(durations)

            # Top domains
            domain_counter: Counter[str] = Counter()
            for crawl_event in self._crawl_events:
                domain = self._extract_domain(crawl_event.url)
                if domain:
                    domain_counter[domain] += 1
            data.top_domains = domain_counter.most_common(top_n)

            # Success/error counts
            data.success_count = sum(1 for ce in self._crawl_events if 200 <= ce.status_code < 400)
            data.error_count = sum(1 for ce in self._crawl_events if ce.status_code >= 400 or ce.error)

        return data

    def get_analytics(self, top_n: int = 10) -> AnalyticsData:
        """Merge search and crawl analytics into one AnalyticsData.

        Calls ``_compute_search_analytics(top_n)`` and
        ``_compute_crawl_analytics(top_n)`` and merges the two results
        into a single AnalyticsData: search fields (total_searches,
        avg_search_duration_ms, top_queries, hourly_searches,
        daily_searches) come from the search result; crawl fields
        (total_crawls, avg_crawl_duration_ms, top_domains, error_count,
        success_count) come from the crawl result. ``total_pages_indexed``
        is never set by either sub-compute, so it stays the dataclass
        default 0. When both event lists are empty, both sub-computes
        return a default AnalyticsData, so the merged result is all
        zeros/empty.
        """
        search_data = self._compute_search_analytics(top_n)
        crawl_data = self._compute_crawl_analytics(top_n)

        return AnalyticsData(
            total_searches=search_data.total_searches,
            total_crawls=crawl_data.total_crawls,
            avg_search_duration_ms=search_data.avg_search_duration_ms,
            avg_crawl_duration_ms=crawl_data.avg_crawl_duration_ms,
            top_queries=search_data.top_queries,
            top_domains=crawl_data.top_domains,
            hourly_searches=search_data.hourly_searches,
            daily_searches=search_data.daily_searches,
            error_count=crawl_data.error_count,
            success_count=crawl_data.success_count,
        )

    def get_search_events(self, limit: int | None = None) -> list[SearchEvent]:
        """Return the recorded search events in order.

        A positive ``limit`` returns only the last ``limit`` events
        (the most recent tail). A falsy ``limit`` (``None`` or ``0``)
        returns all recorded events.
        """
        events = self._search_events
        if limit:
            events = events[-limit:]
        return events

    def get_crawl_events(self, limit: int | None = None) -> list[CrawlEvent]:
        """Return the recorded crawl events in order.

        A positive ``limit`` returns only the last ``limit`` events
        (the most recent tail). A falsy ``limit`` (``None`` or ``0``)
        returns all recorded events.
        """
        events = self._crawl_events
        if limit:
            events = events[-limit:]
        return events

    def get_search_stats(self) -> dict[str, Any]:
        """Compute per-search statistics over the recorded search events.

        Guard path: when no search events have been recorded, returns
        exactly ``{"total": 0}`` (no other keys).

        Normal path: returns a dict with these fields:
            total: number of recorded search events.
            avg_results: mean of each event's result_count.
            max_results / min_results: max / min result_count.
            avg_duration_ms / max_duration_ms: computed only over events
                whose duration_ms > 0 (0 when none qualify).
            click_through_rate: fraction of events with a truthy
                clicked_url (clicked / total).
            unique_queries: count of distinct query strings.
        """
        if not self._search_events:
            return {"total": 0}

        result_counts = [e.result_count for e in self._search_events]
        durations = [e.duration_ms for e in self._search_events if e.duration_ms > 0]
        clicked = sum(1 for e in self._search_events if e.clicked_url)

        return {
            "total": len(self._search_events),
            "avg_results": sum(result_counts) / len(result_counts) if result_counts else 0,
            "max_results": max(result_counts) if result_counts else 0,
            "min_results": min(result_counts) if result_counts else 0,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
            "max_duration_ms": max(durations) if durations else 0,
            "click_through_rate": clicked / len(self._search_events) if self._search_events else 0,
            "unique_queries": len({e.query for e in self._search_events}),
        }

    def get_crawl_stats(self) -> dict[str, Any]:
        """Compute per-crawl statistics over the recorded crawl events.

        Guard path: when no crawl events have been recorded, returns
        exactly ``{"total": 0}`` (no other keys).

        Normal path: returns a dict with these fields:
            total: number of recorded crawl events.
            avg_duration_ms: mean duration_ms over events whose
                duration_ms > 0 (0 when none qualify).
            avg_content_size: mean content_size over events whose
                content_size > 0 (0 when none qualify).
            total_content_size: sum of content_size over the same
                content_size > 0 events (0 when none qualify).
            status_codes: dict mapping each status_code to its count
                over ALL events (a Counter, not filtered).
            error_rate: fraction of events with a truthy error
                (error events / total).
        """
        if not self._crawl_events:
            return {"total": 0}

        durations = [e.duration_ms for e in self._crawl_events if e.duration_ms > 0]
        sizes = [e.content_size for e in self._crawl_events if e.content_size > 0]
        status_codes = Counter(e.status_code for e in self._crawl_events)

        return {
            "total": len(self._crawl_events),
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
            "avg_content_size": sum(sizes) / len(sizes) if sizes else 0,
            "total_content_size": sum(sizes),
            "status_codes": dict(status_codes),
            "error_rate": sum(1 for e in self._crawl_events if e.error) / len(self._crawl_events),
        }

    def save(self, path: str) -> str:
        """Save analytics data to JSON file."""
        data = {
            "search_events": [
                {
                    "query": e.query,
                    "timestamp": e.timestamp,
                    "result_count": e.result_count,
                    "clicked_url": e.clicked_url,
                    "duration_ms": e.duration_ms,
                }
                for e in self._search_events
            ],
            "crawl_events": [
                {
                    "url": e.url,
                    "timestamp": e.timestamp,
                    "status_code": e.status_code,
                    "content_size": e.content_size,
                    "duration_ms": e.duration_ms,
                    "error": e.error,
                }
                for e in self._crawl_events
            ],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return path

    def load(self, path: str) -> int:
        """Load analytics data from JSON file. Returns total events loaded."""
        path_obj = Path(path)
        if not path_obj.exists():
            return 0

        with open(path_obj) as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                return 0

        if not isinstance(data, dict):
            return 0

        self._search_events.clear()
        self._crawl_events.clear()

        for item in data.get("search_events", []):
            self._search_events.append(SearchEvent(**item))

        for item in data.get("crawl_events", []):
            self._crawl_events.append(CrawlEvent(**item))

        return len(self._search_events) + len(self._crawl_events)

    def clear(self) -> None:
        """Clear all tracked events."""
        self._search_events.clear()
        self._crawl_events.clear()

    @staticmethod
    def _extract_domain(url: str) -> str | None:
        """Extract the host segment from a URL.

        Returns None for a falsy url (empty string or None). For a
        scheme-prefixed url (one containing "://") returns the segment
        between "://" and the first "/" (the host, including any port;
        the port is not stripped). For a scheme-less url returns the
        segment before the first "/". Returns None if the split raises
        IndexError or AttributeError. Unlike url_utils.extract_domain,
        this does not strip a port and does not lowercase.
        """
        if not url:
            return None
        try:
            # Simple domain extraction
            return url.split("://")[1].split("/")[0] if "://" in url else url.split("/")[0]
        except (IndexError, AttributeError):
            return None
