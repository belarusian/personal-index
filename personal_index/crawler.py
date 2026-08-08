"""Web crawler module with configurable depth, politeness, and rate limiting."""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse


@dataclass
class CrawlConfig:
    """Configuration for the web crawler."""
    max_depth: int = 3
    politeness_delay: float = 1.0  # seconds between requests to same host
    rate_limit: int = 10  # max requests per minute per host
    timeout: int = 30  # request timeout in seconds
    max_pages: int = 1000  # maximum pages to crawl
    user_agent: str = "PersonalIndex/0.1.0"
    allowed_domains: List[str] = field(default_factory=list)
    blocked_paths: List[str] = field(default_factory=list)


@dataclass
class CrawlResult:
    """Result of crawling a single page."""
    url: str
    title: str = ""
    content: str = ""
    links: List[str] = field(default_factory=list)
    status_code: int = 0
    error: Optional[str] = None
    depth: int = 0
    crawled_at: float = field(default_factory=time.time)


class RateLimiter:
    """Token bucket rate limiter per host."""

    def __init__(self, rate: int = 10):
        self.rate = rate  # requests per minute
        self.tokens: Dict[str, float] = {}
        self.last_refill: Dict[str, float] = {}

    def _refill(self, host: str) -> None:
        now = time.time()
        if host not in self.tokens:
            self.tokens[host] = self.rate
            self.last_refill[host] = now
            return
        elapsed = now - self.last_refill[host]
        new_tokens = elapsed * (self.rate / 60.0)
        self.tokens[host] = min(self.rate, self.tokens[host] + new_tokens)
        self.last_refill[host] = now

    def acquire(self, host: str) -> bool:
        """Try to acquire a token for the given host. Returns True if allowed."""
        self._refill(host)
        if self.tokens.get(host, 0) >= 1:
            self.tokens[host] -= 1
            return True
        return False

    def wait_time(self, host: str) -> float:
        """Return seconds to wait before next request."""
        self._refill(host)
        if self.tokens.get(host, 0) >= 1:
            return 0.0
        deficit = 1 - self.tokens[host]
        return deficit * (60.0 / self.rate)


class WebCrawler:
    """Configurable web crawler with politeness and rate limiting."""

    def __init__(self, config: Optional[CrawlConfig] = None):
        self.config = config or CrawlConfig()
        self.rate_limiter = RateLimiter(self.config.rate_limit)
        self.crawled_urls: Set[str] = set()
        self.results: List[CrawlResult] = []
        self.host_delay: Dict[str, float] = {}

    def _get_host(self, url: str) -> str:
        """Extract hostname from URL."""
        return urlparse(url).hostname or ""

    def _is_allowed(self, url: str) -> bool:
        """Check if URL is allowed by configuration."""
        parsed = urlparse(url)
        host = parsed.hostname or ""

        # Check allowed domains
        if self.config.allowed_domains:
            if host not in self.config.allowed_domains:
                return False

        # Check blocked paths
        for blocked in self.config.blocked_paths:
            if blocked in parsed.path:
                return False

        return True

    def _apply_politeness(self, url: str) -> None:
        """Apply politeness delay between requests to same host."""
        host = self._get_host(url)
        now = time.time()
        last = self.host_delay.get(host, 0)
        wait = self.config.politeness_delay - (now - last)
        if wait > 0:
            time.sleep(wait)
        self.host_delay[host] = time.time()

    def _resolve_links(self, base_url: str, raw_links: List[str]) -> List[str]:
        """Resolve relative links to absolute URLs."""
        resolved = []
        for link in raw_links:
            try:
                absolute = urljoin(base_url, link.strip())
                if self._is_allowed(absolute) and absolute not in self.crawled_urls:
                    resolved.append(absolute)
            except Exception:
                continue
        return resolved

    def crawl(self, start_url: str, depth: int = 0) -> List[CrawlResult]:
        """Crawl starting from a URL up to max_depth.

        This is a synchronous simulation method. In production, this would
        use aiohttp or similar for actual HTTP requests.
        """
        if depth > self.config.max_depth:
            return []

        if start_url in self.crawled_urls:
            return []

        if len(self.crawled_urls) >= self.config.max_pages:
            return []

        if not self._is_allowed(start_url):
            return []

        host = self._get_host(start_url)
        if not self.rate_limiter.acquire(host):
            wait = self.rate_limiter.wait_time(host)
            time.sleep(min(wait, 5))

        self._apply_politeness(start_url)
        self.crawled_urls.add(start_url)

        # Simulate crawl result (in production, this would make HTTP requests)
        result = CrawlResult(
            url=start_url,
            depth=depth,
            status_code=200,
        )
        self.results.append(result)

        # Recurse into links if available
        if depth < self.config.max_depth:
            for link in result.links:
                self.crawl(link, depth + 1)

        return self.results

    def get_stats(self) -> Dict:
        """Return crawl statistics."""
        return {
            "total_crawled": len(self.crawled_urls),
            "total_results": len(self.results),
            "unique_hosts": len(set(self._get_host(r.url) for r in self.results)),
        }
