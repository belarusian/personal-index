"""Web crawler for personal-index.

Handles fetching web pages with configurable depth, politeness,
and rate limiting. Extracts links for further crawling.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

from personal_index.models import CrawledPage, CrawlConfig, CrawlStats
from personal_index.filter import ContentFilter

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter that enforces delays between requests."""

    def __init__(self, rate_limit: float = 1.0, politeness_delay: float = 0.5):
        self.rate_limit = rate_limit
        self.politeness_delay = politeness_delay
        self._last_request_time: float = 0
        self._last_request_per_host: dict[str, float] = {}

    def wait(self, url: str) -> None:
        """Wait before making a request to respect rate limits."""
        now = time.time()
        parsed = urlparse(url)
        host = parsed.netloc

        # Global rate limit
        elapsed_since_last = now - self._last_request_time
        if elapsed_since_last < self.rate_limit:
            time.sleep(self.rate_limit - elapsed_since_last)

        # Per-host politeness delay
        if host in self._last_request_per_host:
            elapsed_since_host = now - self._last_request_per_host[host]
            if elapsed_since_host < self.politeness_delay:
                time.sleep(self.politeness_delay - elapsed_since_host)

        self._last_request_time = time.time()
        self._last_request_per_host[host] = time.time()


class LinkExtractor:
    """Extracts links from HTML content."""

    @staticmethod
    def extract_links(html: str, base_url: str) -> list[str]:
        """Extract all unique, absolute links from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        links = set()
        for tag in soup.find_all("a", href=True):
            href = tag["href"]
            if not isinstance(href, str):
                continue
            # Skip javascript, mailto, tel, anchor-only links
            if href.startswith(("javascript:", "mailto:", "tel:", "#")):
                continue
            # Resolve relative URLs
            absolute_url = urljoin(base_url, href)
            # Normalize: remove fragment
            parsed = urlparse(absolute_url)
            normalized = parsed._replace(fragment="").geturl()
            if normalized.startswith(("http://", "https://")):
                links.add(normalized)
        return list(links)


class PageParser:
    """Parses HTML content into structured data."""

    @staticmethod
    def parse(html: str, url: str) -> CrawledPage:
        """Parse HTML into a CrawledPage."""
        soup = BeautifulSoup(html, "html.parser")

        # Extract title
        title = ""
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            title = str(title_tag.string).strip()

        # Extract meta description
        meta_description = ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            meta_description = str(meta_desc["content"]).strip()

        # Extract text content
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()
        content = soup.get_text(separator="\n", strip=True)

        # Truncate very long content
        max_length = 50000
        if len(content) > max_length:
            content = content[:max_length]

        word_count = len(content.split())

        return CrawledPage(
            url=url,
            title=title,
            content=content,
            meta_description=meta_description,
            word_count=word_count,
        )


class WebCrawler:
    """Web crawler with configurable depth, politeness, and rate limiting."""

    def __init__(
        self,
        config: Optional[CrawlConfig] = None,
        content_filter: Optional[ContentFilter] = None,
    ):
        self.config = config or CrawlConfig()
        self.content_filter = content_filter
        self.rate_limiter = RateLimiter(
            rate_limit=self.config.rate_limit,
            politeness_delay=self.config.politeness_delay,
        )
        self._visited: set[str] = set()
        self._queue: deque[tuple[str, int, Optional[str]]] = deque()
        self.stats = CrawlStats()
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": self.config.user_agent,
        })

    def crawl(self, seed_urls: list[str]) -> CrawlStats:
        """Start crawling from seed URLs.

        Args:
            seed_urls: Initial URLs to crawl from.

        Returns:
            CrawlStats with statistics about the crawl.
        """
        self.stats.start_time = datetime.utcnow()
        self._visited.clear()
        self._queue.clear()

        for url in seed_urls:
            self._enqueue(url, depth=0, parent=None)

        while self._queue and self.stats.pages_crawled < self.config.max_pages:
            url, depth, parent_url = self._queue.popleft()

            if url in self._visited:
                continue

            if depth > self.config.max_depth:
                continue

            # Check domain restrictions
            if not self._is_allowed_domain(url):
                continue

            self._visited.add(url)
            self.stats.pages_crawled += 1

            logger.info(f"Crawling [{self.stats.pages_crawled}]: {url}")

            try:
                page = self._fetch_and_parse(url, depth, parent_url)
                if page:
                    self._process_page(page)
            except Exception as e:
                self.stats.errors += 1
                logger.warning(f"Error crawling {url}: {e}")

        self.stats.end_time = datetime.utcnow()
        return self.stats

    def _enqueue(
        self, url: str, depth: int, parent: Optional[str]
    ) -> None:
        """Add a URL to the crawl queue."""
        if url not in self._visited:
            self._queue.append((url, depth + 1, parent))
            self.stats.urls_queued += 1

    def _is_allowed_domain(self, url: str) -> bool:
        """Check if URL domain is allowed."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        if self.config.blocked_domains:
            for blocked in self.config.blocked_domains:
                if blocked.lower() in domain:
                    return False

        if self.config.allowed_domains:
            for allowed in self.config.allowed_domains:
                if allowed.lower() in domain:
                    return True
            return False

        return True

    def _fetch_and_parse(
        self, url: str, depth: int, parent_url: Optional[str]
    ) -> Optional[CrawledPage]:
        """Fetch a URL and parse its content."""
        self.rate_limiter.wait(url)

        response = self._session.get(
            url,
            timeout=self.config.timeout,
            allow_redirects=True,
        )
        response.raise_for_status()

        # Check content length
        content_length = len(response.content)
        if content_length > self.config.max_content_length:
            logger.warning(f"Skipping {url}: content too large ({content_length} bytes)")
            return None

        # Check content type
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            logger.debug(f"Skipping {url}: not HTML (content-type: {content_type})")
            return None

        page = PageParser.parse(response.text, url)
        page.status_code = response.status_code
        page.depth = depth
        page.parent_url = parent_url
        page.headers = dict(response.headers)

        return page

    def _process_page(self, page: CrawledPage) -> None:
        """Process a crawled page: filter, store, extract links."""
        # Apply content filter
        if self.content_filter:
            filter_result = self.content_filter.filter_page(page)
            if not filter_result.passed:
                self.stats.pages_filtered += 1
                logger.debug(f"Filtered out: {page.url}")
                return

        self.stats.pages_stored += 1

        # Extract and queue links for further crawling
        if page.depth < self.config.max_depth:
            try:
                links = LinkExtractor.extract_links(
                    f"<html><body>{page.content}</body></html>",
                    page.url,
                )
                for link in links:
                    self._enqueue(link, page.depth, page.url)
            except Exception as e:
                logger.debug(f"Error extracting links from {page.url}: {e}")

    def get_visited_urls(self) -> set[str]:
        """Return set of visited URLs."""
        return self._visited.copy()

    def get_queue_size(self) -> int:
        """Return current queue size."""
        return len(self._queue)
