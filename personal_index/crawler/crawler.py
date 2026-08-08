"""Web crawler with configurable depth, politeness, and rate limiting."""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

import requests
from requests.exceptions import ConnectionError, Timeout, RequestException

from personal_index.config import CrawlerConfig
from personal_index.filter import ContentFilter
from personal_index.models import Page, PageStatus, URL
from personal_index.utils import (
    extract_links,
    extract_meta_description,
    extract_text_content,
    extract_title,
    normalize_url,
)


class WebCrawler:
    """Web crawler that respects politeness and rate limiting."""

    def __init__(
        self,
        config: Optional[CrawlerConfig] = None,
        content_filter: Optional[ContentFilter] = None,
    ) -> None:
        """Initialize the web crawler.

        Args:
            config: Crawler configuration. Uses defaults if None.
            content_filter: Optional content filter for pre/post-crawl filtering.
        """
        self.config = config or CrawlerConfig()
        self.content_filter = content_filter
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.config.user_agent})

        # Tracking
        self._crawled_urls: set[str] = set()
        self._domain_counts: dict[str, int] = defaultdict(int)
        self._last_request_time: dict[str, float] = {}
        self._crawl_stats: dict[str, int] = defaultdict(int)

    @property
    def stats(self) -> dict[str, int]:
        """Get crawl statistics."""
        return dict(self._crawl_stats)

    def crawl(
        self,
        seed_urls: list[str],
        max_depth: Optional[int] = None,
    ) -> list[Page]:
        """Crawl starting from seed URLs.

        Args:
            seed_urls: List of starting URLs.
            max_depth: Override max depth from config.

        Returns:
            List of crawled pages that passed content filtering.
        """
        max_depth = max_depth if max_depth is not None else self.config.max_depth
        self._crawled_urls.clear()
        self._domain_counts.clear()
        self._last_request_time.clear()
        self._crawl_stats.clear()

        # Initialize seed URLs
        queue: list[URL] = []
        for url_str in seed_urls:
            normalized = normalize_url(url_str)
            if normalized:
                queue.append(URL(url=normalized, depth=0))
                self._crawled_urls.add(normalized)

        results: list[Page] = []

        while queue:
            current = queue.pop(0)

            # Check domain limit
            if self._domain_counts[current.domain] >= self.config.max_pages_per_domain:
                current.status = PageStatus.SKIPPED
                self._crawl_stats["skipped_domain_limit"] += 1
                continue

            # Crawl the page
            page = self._fetch_page(current)
            if page is None:
                continue

            # Apply content filter
            if self.content_filter:
                filter_result = self.content_filter.filter_page(page)
                self.content_filter.update_page(page, filter_result)
                if not filter_result.passed:
                    self._crawl_stats["filtered_out"] += 1
                    continue

            results.append(page)
            self._crawl_stats["indexed"] += 1

            # Extract and queue links if within depth
            if current.depth < max_depth:
                for link in page.links:
                    normalized = normalize_url(link, current.url)
                    if (
                        normalized
                        and normalized not in self._crawled_urls
                        and self._should_crawl(normalized)
                    ):
                        self._crawled_urls.add(normalized)
                        self._domain_counts[normalized.split("/")[2].split(":")[0]] += 1
                        queue.append(
                            URL(
                                url=normalized,
                                depth=current.depth + 1,
                                parent_url=current.url,
                            )
                        )

        self._crawl_stats["total_crawled"] = len(self._crawled_urls)
        return results

    def _fetch_page(self, url_obj: URL) -> Optional[Page]:
        """Fetch and parse a single page.

        Args:
            url_obj: The URL to fetch.

        Returns:
            Parsed Page object, or None if fetch failed.
        """
        # Rate limiting
        self._apply_rate_limit(url_obj.domain)

        try:
            response = self.session.get(
                url_obj.url,
                timeout=self.config.timeout,
                allow_redirects=True,
            )

            if response.status_code != 200:
                url_obj.status = PageStatus.FAILED
                url_obj.error = f"HTTP {response.status_code}"
                self._crawl_stats["failed_http"] += 1
                return None

            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                url_obj.status = PageStatus.SKIPPED
                self._crawl_stats["skipped_not_html"] += 1
                return None

            content = response.text
            if len(content) > self.config.max_content_size:
                url_obj.status = PageStatus.SKIPPED
                self._crawl_stats["skipped_too_large"] += 1
                return None

            # Parse page
            page = Page(
                url=response.url,
                title=extract_title(content),
                content=extract_text_content(content),
                meta_description=extract_meta_description(content),
                links=extract_links(content, response.url),
                crawled_at=datetime.now(timezone.utc),
                status_code=response.status_code,
                content_type=content_type,
                content_length=len(content),
            )

            url_obj.status = PageStatus.CRAWLED
            url_obj.crawled_at = page.crawled_at
            self._crawl_stats["crawled"] += 1
            return page

        except (ConnectionError, Timeout) as e:
            url_obj.status = PageStatus.FAILED
            url_obj.error = str(e)
            self._crawl_stats["failed_network"] += 1
            return None
        except RequestException as e:
            url_obj.status = PageStatus.FAILED
            url_obj.error = str(e)
            self._crawl_stats["failed_request"] += 1
            return None

    def _apply_rate_limit(self, domain: str) -> None:
        """Apply rate limiting for a domain.

        Args:
            domain: The domain to rate limit for.
        """
        last_time = self._last_request_time.get(domain, 0)
        elapsed = time.time() - last_time
        delay = self.config.politeness_delay - elapsed
        if delay > 0:
            time.sleep(delay)
        self._last_request_time[domain] = time.time()

    def _should_crawl(self, url: str) -> bool:
        """Check if a URL should be crawled.

        Args:
            url: The URL to check.

        Returns:
            True if the URL should be crawled.
        """
        # Pre-filter by content filter if available
        if self.content_filter:
            if self.content_filter.filter_url_pre_crawl(url):
                return True

        return True

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self) -> WebCrawler:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
