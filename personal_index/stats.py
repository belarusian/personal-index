"""Statistics and analytics for the personal-index system."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from personal_index.interest_store import InterestStore
from personal_index.search_index import SearchIndex


@dataclass
class IndexStats:
    """Statistics about the search index."""

    total_pages: int = 0
    total_words: int = 0
    unique_domains: int = 0
    avg_content_length: float = 0.0
    pages_with_interests: int = 0
    top_domains: list[tuple[str, int]] = field(default_factory=list)
    top_interests: list[tuple[str, int]] = field(default_factory=list)
    oldest_page: Optional[datetime] = None
    newest_page: Optional[datetime] = None


@dataclass
class CrawlStats:
    """Statistics about crawling activity."""

    total_crawls: int = 0
    total_pages_crawled: int = 0
    total_pages_indexed: int = 0
    total_errors: int = 0
    avg_crawl_duration: float = 0.0
    last_crawl: Optional[datetime] = None
    pages_per_crawl: list[int] = field(default_factory=list)


class StatsCollector:
    """Collect and compute statistics about the system."""

    def __init__(
        self,
        interest_store: Optional[InterestStore] = None,
        search_index: Optional[SearchIndex] = None,
    ):
        self.interest_store = interest_store
        self.search_index = search_index

    def get_index_stats(self) -> IndexStats:
        """Compute statistics about the search index."""
        if not self.search_index:
            return IndexStats()

        stats = IndexStats()
        pages = list(self.search_index._documents.values())
        stats.total_pages = len(pages)

        if not pages:
            return stats

        # Count words
        total_words = 0
        total_content_length = 0
        domains = Counter()
        interests = Counter()
        dates = []

        for page in pages:
            content = f"{page.title} {page.content} {page.meta_description}"
            words = len(content.split())
            total_words += words
            total_content_length += len(page.content)

            # Extract domain
            from urllib.parse import urlparse
            domain = urlparse(page.url).netloc
            if domain:
                domains[domain] += 1

            # Count interests
            for interest_name in page.matched_interests:
                interests[interest_name] += 1
            if page.matched_interests:
                stats.pages_with_interests += 1

            # Track dates
            dates.append(page.crawled_at)

        stats.total_words = total_words
        stats.avg_content_length = total_content_length / max(len(pages), 1)
        stats.unique_domains = len(domains)
        stats.top_domains = domains.most_common(10)
        stats.top_interests = interests.most_common(10)

        if dates:
            stats.oldest_page = min(dates)
            stats.newest_page = max(dates)

        return stats

    def format_index_stats(self) -> str:
        """Format index statistics as a readable string."""
        stats = self.get_index_stats()
        lines = [
            "=== Index Statistics ===",
            f"Total pages: {stats.total_pages}",
            f"Total words: {stats.total_words:,}",
            f"Unique domains: {stats.unique_domains}",
            f"Avg content length: {stats.avg_content_length:.0f} chars",
            f"Pages with interests: {stats.pages_with_interests}",
        ]

        if stats.top_domains:
            lines.append("\nTop domains:")
            for domain, count in stats.top_domains[:5]:
                lines.append(f"  {domain}: {count}")

        if stats.top_interests:
            lines.append("\nTop matched interests:")
            for interest, count in stats.top_interests[:5]:
                lines.append(f"  {interest}: {count}")

        if stats.oldest_page:
            lines.append(f"\nOldest page: {stats.oldest_page:%Y-%m-%d %H:%M}")
        if stats.newest_page:
            lines.append(f"Newest page: {stats.newest_page:%Y-%m-%d %H:%M}")

        return "\n".join(lines)
