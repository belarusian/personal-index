"""Crawl statistics tracking and reporting."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DomainStats:
    """Statistics for a single domain."""

    domain: str
    urls_crawled: int = 0
    urls_failed: int = 0
    urls_skipped: int = 0
    total_bytes: int = 0
    avg_response_time: float = 0.0
    response_times: list[float] = field(default_factory=list)
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    status_codes: dict[int, int] = field(default_factory=lambda: defaultdict(int))

    @property
    def success_rate(self) -> float:
        """Ratio of successful URLs to total attempted."""
        total = self.urls_crawled + self.urls_failed
        return self.urls_crawled / total if total > 0 else 0.0

    @property
    def total_requests(self) -> int:
        """Total number of requests (crawled + failed + skipped)."""
        return self.urls_crawled + self.urls_failed + self.urls_skipped

    def record_success(self, bytes_downloaded: int = 0, response_time: float = 0.0, status_code: int = 200) -> None:
        """Record a successful URL crawl.

        Args:
            bytes_downloaded: Number of bytes downloaded.
            response_time: Response time in seconds.
            status_code: HTTP status code.
        """
        self.urls_crawled += 1
        self.total_bytes += bytes_downloaded
        self.response_times.append(response_time)
        self.status_codes[status_code] += 1
        self.last_seen = time.time()
        if self.response_times:
            self.avg_response_time = sum(self.response_times) / len(self.response_times)

    def record_failure(self, error: str = "", status_code: int = 0) -> None:
        """Record a failed URL crawl.

        Args:
            error: Error message.
            status_code: HTTP status code if available.
        """
        self.urls_failed += 1
        if status_code:
            self.status_codes[status_code] += 1
        self.last_seen = time.time()

    def record_skip(self) -> None:
        """Record a skipped URL."""
        self.urls_skipped += 1
        self.last_seen = time.time()

    def to_dict(self) -> dict:
        """Serialize domain stats to a dictionary.

        Returns:
            Dictionary representation of the domain stats.
        """
        return {
            "domain": self.domain,
            "urls_crawled": self.urls_crawled,
            "urls_failed": self.urls_failed,
            "urls_skipped": self.urls_skipped,
            "total_bytes": self.total_bytes,
            "avg_response_time": round(self.avg_response_time, 3),
            "success_rate": round(self.success_rate, 3),
            "total_requests": self.total_requests,
            "status_codes": dict(self.status_codes),
        }


class CrawlStats:
    """Tracks crawl statistics across all domains."""

    def __init__(self):
        self._domains: dict[str, DomainStats] = {}
        self._start_time: float = time.time()
        self._total_urls: int = 0
        self._total_bytes: int = 0
        self._errors: list[str] = []

    def get_domain_stats(self, domain: str) -> DomainStats:
        """Get or create stats for a domain.

        Args:
            domain: The domain name.

        Returns:
            DomainStats for the given domain.
        """
        if domain not in self._domains:
            self._domains[domain] = DomainStats(domain=domain)
        return self._domains[domain]

    def record_url_crawled(self, domain: str, bytes_downloaded: int = 0,
                           response_time: float = 0.0, status_code: int = 200) -> None:
        """Record a successfully crawled URL.

        Args:
            domain: The domain of the URL.
            bytes_downloaded: Number of bytes downloaded.
            response_time: Response time in seconds.
            status_code: HTTP status code.
        """
        stats = self.get_domain_stats(domain)
        stats.record_success(bytes_downloaded, response_time, status_code)
        self._total_urls += 1
        self._total_bytes += bytes_downloaded

    def record_url_failed(self, domain: str, error: str = "", status_code: int = 0) -> None:
        """Record a failed URL crawl.

        Args:
            domain: The domain of the URL.
            error: Error message.
            status_code: HTTP status code if available.
        """
        stats = self.get_domain_stats(domain)
        stats.record_failure(error, status_code)
        self._total_urls += 1
        if error:
            self._errors.append(error)

    def record_url_skipped(self, domain: str) -> None:
        """Record a skipped URL.

        Args:
            domain: The domain of the URL.
        """
        stats = self.get_domain_stats(domain)
        stats.record_skip()

    @property
    def uptime(self) -> float:
        """Seconds since crawl tracking started."""
        return time.time() - self._start_time

    @property
    def domain_count(self) -> int:
        """Number of unique domains tracked."""
        return len(self._domains)

    @property
    def total_urls(self) -> int:
        """Total number of URLs processed."""
        return self._total_urls

    @property
    def total_bytes(self) -> int:
        """Total bytes downloaded across all URLs."""
        return self._total_bytes

    @property
    def error_count(self) -> int:
        """Number of errors recorded."""
        return len(self._errors)

    def get_summary(self) -> dict:
        """Get an overall summary of crawl statistics.

        Returns:
            Dictionary with aggregate crawl stats.
        """
        total_crawled = sum(d.urls_crawled for d in self._domains.values())
        total_failed = sum(d.urls_failed for d in self._domains.values())
        total_skipped = sum(d.urls_skipped for d in self._domains.values())
        return {
            "uptime_seconds": round(self.uptime, 2),
            "total_urls": self._total_urls,
            "total_bytes": self._total_bytes,
            "total_crawled": total_crawled,
            "total_failed": total_failed,
            "total_skipped": total_skipped,
            "domain_count": self.domain_count,
            "error_count": self.error_count,
            "overall_success_rate": round(total_crawled / (total_crawled + total_failed), 3) if (total_crawled + total_failed) > 0 else 0.0,
        }

    def get_domain_summaries(self) -> list[dict]:
        """Get per-domain summaries.

        Returns:
            List of domain stat dictionaries.
        """
        return [d.to_dict() for d in self._domains.values()]

    def reset(self) -> None:
        """Reset all crawl statistics."""
        self._domains.clear()
        self._start_time = time.time()
        self._total_urls = 0
        self._total_bytes = 0
        self._errors.clear()
