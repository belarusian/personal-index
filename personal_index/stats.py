"""Statistics collection and reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from personal_index.interest_store import InterestStore
from personal_index.search_index import SearchIndex
from personal_index.url_utils import extract_domain


@dataclass
class IndexStats:
    """Statistics about the search index."""

    total_pages: int = 0
    total_words: int = 0
    unique_domains: int = 0
    avg_content_length: float = 0.0
    pages_with_interests: int = 0
    top_domains: List[Tuple[str, int]] = field(default_factory=list)
    top_interests: List[Tuple[str, int]] = field(default_factory=list)
    oldest_page: Optional[datetime] = None
    newest_page: Optional[datetime] = None


@dataclass
class CrawlStats:
    """Statistics about crawling activity."""

    total_crawls: int = 0
    total_pages_crawled: int = 0
    total_errors: int = 0
    total_bytes_fetched: int = 0


@dataclass
class StatsCollector:
    """Collects and reports statistics."""

    interest_store: Optional[InterestStore] = None
    search_index: Optional[SearchIndex] = None

    def get_index_stats(self) -> IndexStats:
        """Calculate current index statistics."""
        stats = IndexStats()
        if not self.search_index:
            return stats

        pages = self.search_index.urls()
        stats.total_pages = len(pages)

        domain_counts: Dict[str, int] = {}
        interest_counts: Dict[str, int] = {}
        total_words = 0
        total_content_length = 0
        pages_with_interests = 0
        timestamps = []

        for url in pages:
            page = self.search_index.get(url)
            if page is None:
                continue

            total_words += len(page.content.split())
            total_content_length += len(page.content)

            domain = extract_domain(url)
            if domain:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1

            for interest_name in page.matched_interests:
                interest_counts[interest_name] = (
                    interest_counts.get(interest_name, 0) + 1
                )
                pages_with_interests += 1

            if page.crawled_at:
                timestamps.append(page.crawled_at)

        stats.total_words = total_words
        stats.unique_domains = len(domain_counts)
        stats.avg_content_length = (
            total_content_length / max(stats.total_pages, 1)
        )
        stats.pages_with_interests = pages_with_interests
        stats.top_domains = sorted(
            domain_counts.items(),
            key=lambda x: x[1], reverse=True
        )[:10]
        stats.top_interests = sorted(
            interest_counts.items(),
            key=lambda x: x[1], reverse=True
        )[:10]

        if timestamps:
            stats.oldest_page = min(timestamps)
            stats.newest_page = max(timestamps)

        return stats

    def format_index_stats(self) -> str:
        """Format index statistics as a string."""
        stats = self.get_index_stats()
        lines = [
            "=== Index Statistics ===",
            f"Total pages: {stats.total_pages}",
            f"Total words: {stats.total_words}",
            f"Unique domains: {stats.unique_domains}",
            f"Avg content length: {stats.avg_content_length:.0f}",
            f"Pages with interests: {stats.pages_with_interests}",
        ]

        if stats.top_domains:
            lines.append("\nTop domains:")
            for domain, count in stats.top_domains:
                lines.append(f"  {domain}: {count}")

        if stats.top_interests:
            lines.append("\nTop interests:")
            for interest, count in stats.top_interests:
                lines.append(f"  {interest}: {count}")

        if stats.oldest_page:
            lines.append(f"\nOldest page: {stats.oldest_page}")
        if stats.newest_page:
            lines.append(f"Newest page: {stats.newest_page}")

        return "\n".join(lines)
