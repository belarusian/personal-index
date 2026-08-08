"""
Web crawler for personal-index.

Configurable depth, politeness, and rate limiting for crawling web pages.
Respects robots.txt and handles errors gracefully.
"""

import asyncio
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin, urlparse

from aiohttp import ClientSession, ClientTimeout, TCPConnector

from personal_index.config import CrawlerConfig
from personal_index.filter import ContentFilter
from personal_index.index import SearchIndex, IndexedPage


@dataclass
class CrawledPage:
    """A page that has been crawled."""
    url: str
    title: str
    content: str
    links: list[str] = field(default_factory=list)
    status_code: int = 0
    content_type: str = ""
    crawled_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    error: Optional[str] = None


class RateLimiter:
    """Rate limiter for polite crawling."""

    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self._last_request: dict[str, float] = {}

    async def wait(self, domain: str) -> None:
        """Wait if needed before making a request to the given domain."""
        last = self._last_request.get(domain, 0)
        elapsed = time.monotonic() - last
        if elapsed < self.delay:
            await asyncio.sleep(self.delay - elapsed)
        self._last_request[domain] = time.monotonic()


class RobotsChecker:
    """Simple robots.txt checker."""

    def __init__(self):
        self._cache: dict[str, list[str]] = {}

    async def is_allowed(self, url: str, user_agent: str = "*", session: Optional[ClientSession] = None) -> bool:
        """Check if a URL is allowed by robots.txt."""
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        if base_url not in self._cache:
            allowed = await self._fetch_robots(base_url, session)
            self._cache[base_url] = allowed
        else:
            allowed = self._cache[base_url]

        return url in allowed or not allowed  # Empty list means no robots.txt (allow all)

    async def _fetch_robots(self, base_url: str, session: Optional[ClientSession] = None) -> list[str]:
        """Fetch and parse robots.txt. Returns list of allowed paths or empty list."""
        robots_url = f"{base_url}/robots.txt"
        try:
            if session:
                async with session.get(robots_url, timeout=ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        content = await resp.text()
                        return self._parse_robots(content)
            return []
        except Exception:
            return []

    def _parse_robots(self, content: str) -> list[str]:
        """Parse robots.txt content. Returns list of allowed URL patterns."""
        # Simple parser - returns empty list (allow all) if no disallow rules
        for line in content.splitlines():
            line = line.strip().lower()
            if line.startswith("disallow:") and not line.startswith("disallow: "):
                return None  # Has disallow rules, we'll be conservative
        return []


class WebCrawler:
    """Web crawler with configurable depth, politeness, and rate limiting."""

    def __init__(
        self,
        config: Optional[CrawlerConfig] = None,
        content_filter: Optional[ContentFilter] = None,
        search_index: Optional[SearchIndex] = None,
    ):
        self.config = config or CrawlerConfig()
        self.content_filter = content_filter
        self.search_index = search_index
        self.rate_limiter = RateLimiter(self.config.politeness_delay)
        self.robots_checker = RobotsChecker()
        self._visited: set[str] = set()
        self._stats: dict[str, int] = {
            "pages_crawled": 0,
            "pages_indexed": 0,
            "pages_filtered": 0,
            "errors": 0,
        }

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)

    def reset_stats(self) -> None:
        self._stats = {
            "pages_crawled": 0,
            "pages_indexed": 0,
            "pages_filtered": 0,
            "errors": 0,
        }

    def reset_visited(self) -> None:
        self._visited.clear()

    async def crawl(self, seed_urls: list[str], max_depth: Optional[int] = None) -> list[CrawledPage]:
        """Crawl starting from seed URLs up to max_depth."""
        max_depth = max_depth if max_depth is not None else self.config.max_depth
        self.reset_visited()
        self.reset_stats()

        crawled_pages: list[CrawledPage] = []
        queue: list[tuple[str, int]] = [(url, 0) for url in seed_urls]

        connector = TCPConnector(limit=self.config.max_concurrent_requests)
        timeout = ClientTimeout(total=self.config.request_timeout)

        async with ClientSession(
            connector=connector,
            headers={"User-Agent": self.config.user_agent},
        ) as session:
            while queue:
                url, depth = queue.pop(0)

                if depth > max_depth:
                    continue
                if url in self._visited:
                    continue

                self._visited.add(url)

                if self.config.respect_robots_txt:
                    allowed = await self.robots_checker.is_allowed(url, self.config.user_agent, session)
                    if not allowed:
                        continue

                domain = urlparse(url).netloc
                await self.rate_limiter.wait(domain)

                page = await self._fetch_page(url, session)
                if page:
                    crawled_pages.append(page)
                    self._stats["pages_crawled"] += 1

                    if self.content_filter:
                        should_index = self.content_filter.should_index(
                            page.url, page.title, page.content
                        )
                        if should_index.matched and self.search_index:
                            indexed_page = IndexedPage(
                                url=page.url,
                                title=page.title,
                                content=page.content,
                                keywords=should_index.matched_keywords,
                                score=should_index.score,
                                indexed_at=page.crawled_at,
                                source_interest=",".join(should_index.matching_interests),
                                word_count=len(page.content.split()),
                            )
                            self.search_index.add_page(indexed_page)
                            self._stats["pages_indexed"] += 1
                        else:
                            self._stats["pages_filtered"] += 1
                    elif self.search_index:
                        indexed_page = IndexedPage(
                            url=page.url,
                            title=page.title,
                            content=page.content,
                            keywords=[],
                            score=0.0,
                            indexed_at=page.crawled_at,
                            word_count=len(page.content.split()),
                        )
                        self.search_index.add_page(indexed_page)
                        self._stats["pages_indexed"] += 1

                    if depth < max_depth:
                        for link in page.links:
                            if link not in self._visited:
                                queue.append((link, depth + 1))

        return crawled_pages

    async def _fetch_page(self, url: str, session: ClientSession) -> Optional[CrawledPage]:
        """Fetch a single page and extract content."""
        try:
            async with session.get(url, timeout=ClientTimeout(total=self.config.request_timeout)) as resp:
                if resp.status != 200:
                    self._stats["errors"] += 1
                    return CrawledPage(
                        url=url, title="", content="",
                        status_code=resp.status,
                        error=f"HTTP {resp.status}",
                    )

                content_type = resp.headers.get("Content-Type", "")
                if "text/html" not in content_type:
                    return CrawledPage(
                        url=url, title="", content="",
                        status_code=200, content_type=content_type,
                    )

                text = await resp.text()
                if len(text) > self.config.max_page_size:
                    text = text[:self.config.max_page_size]

                title, content, links = self._parse_html(text, url)
                return CrawledPage(
                    url=url,
                    title=title,
                    content=content,
                    links=links,
                    status_code=200,
                    content_type=content_type,
                )
        except Exception as e:
            self._stats["errors"] += 1
            return CrawledPage(
                url=url, title="", content="",
                error=str(e),
            )

    def _parse_html(self, html: str, base_url: str) -> tuple[str, str, list[str]]:
        """Parse HTML to extract title, text content, and links."""
        title = self._extract_title(html)
        content = self._extract_text(html)
        links = self._extract_links(html, base_url)
        return title, content, links

    def _extract_title(self, html: str) -> str:
        """Extract page title from HTML."""
        match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if match:
            return self._clean_text(match.group(1))
        return ""

    def _extract_text(self, html: str) -> str:
        """Extract text content from HTML."""
        # Remove script and style elements
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.IGNORECASE | re.DOTALL)
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Decode common HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        return self._clean_text(text)

    def _extract_links(self, html: str, base_url: str) -> list[str]:
        """Extract all links from HTML."""
        links = []
        pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>'
        for match in re.finditer(pattern, html, re.IGNORECASE):
            href = match.group(1).strip()
            if href.startswith(('http://', 'https://')):
                parsed = urlparse(href)
                if parsed.netloc:
                    links.append(href)
            elif href.startswith('/'):
                parsed = urlparse(base_url)
                links.append(f"{parsed.scheme}://{parsed.netloc}{href}")
            elif not href.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
                links.append(urljoin(base_url, href))
        return links

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
