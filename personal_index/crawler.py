"""Web crawler with configurable depth, politeness, and rate limiting."""

import time
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse

import requests
from requests.exceptions import RequestException

from personal_index.config import CrawlerConfig, Interest
from personal_index.content import ExtractedContent, extract_content
from personal_index.url_utils import (
    is_valid_url,
    normalize_url,
    extract_links,
    get_domain,
    is_same_domain,
    get_url_depth,
)

logger = logging.getLogger(__name__)


@dataclass
class CrawlResult:
    """Result of crawling a single URL."""

    url: str
    success: bool
    content: Optional[ExtractedContent] = None
    error: str = ""
    depth: int = 0
    links_found: int = 0
    crawled_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class RateLimiter:
    """Rate limiter for controlling request frequency."""

    def __init__(self, rate: float = 1.0):
        self.rate = rate
        self.last_request: Dict[str, float] = {}

    def wait(self, domain: str) -> None:
        """Wait if needed to respect rate limit for a domain."""
        now = time.time()
        last = self.last_request.get(domain, 0)
        delay = 1.0 / self.rate
        elapsed = now - last
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self.last_request[domain] = time.time()


class Crawler:
    """Web crawler with configurable depth, politeness, and rate limiting."""

    def __init__(self, config: Optional[CrawlerConfig] = None):
        self.config = config or CrawlerConfig()
        self.rate_limiter = RateLimiter(rate=self.config.rate_limit)
        self.visited: Set[str] = set()
        self.domain_counts: Dict[str, int] = {}
        self.results: List[CrawlResult] = []
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": self.config.user_agent}
        )

    def crawl(
        self,
        seed_urls: List[str],
        interests: List[Interest] = None,
        on_progress=None,
    ) -> List[CrawlResult]:
        """Crawl starting from seed URLs."""
        if interests is None:
            interests = []

        queue = deque()
        for url in seed_urls:
            normalized = normalize_url(url)
            if is_valid_url(normalized) and normalized not in self.visited:
                queue.append((normalized, 0))
                self.visited.add(normalized)

        while queue:
            url, depth = queue.popleft()

            if depth > self.config.max_depth:
                continue

            # Check domain limit
            domain = get_domain(url)
            if self.domain_counts.get(domain, 0) >= self.config.max_pages_per_domain:
                continue

            # Crawl the URL
            result = self._fetch_and_process(url, depth, interests)
            self.results.append(result)
            self.domain_counts[domain] = self.domain_counts.get(domain, 0) + 1

            # Report progress
            if on_progress:
                on_progress(url, depth, result.success)

            # Queue new links if successful
            if result.success and result.content and depth < self.config.max_depth:
                new_links = self._get_next_links(
                    result.content, url, interests
                )
                for link in new_links:
                    normalized = normalize_url(link)
                    if (
                        normalized not in self.visited
                        and is_valid_url(normalized)
                    ):
                        self.visited.add(normalized)
                        link_domain = get_domain(normalized)
                        if self.domain_counts.get(link_domain, 0) < self.config.max_pages_per_domain:
                            queue.append((normalized, depth + 1))

        return self.results

    def _fetch_and_process(
        self, url: str, depth: int, interests: List[Interest]
    ) -> CrawlResult:
        """Fetch a URL and process its content."""
        domain = get_domain(url)
        self.rate_limiter.wait(domain)

        try:
            response = self.session.get(
                url,
                timeout=self.config.timeout,
                allow_redirects=True,
            )

            if response.status_code != 200:
                return CrawlResult(
                    url=url,
                    success=False,
                    error=f"HTTP {response.status_code}",
                    depth=depth,
                )

            # Check content length
            if len(response.content) > self.config.max_content_length:
                return CrawlResult(
                    url=url,
                    success=False,
                    error="Content too large",
                    depth=depth,
                )

            # Check content type
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return CrawlResult(
                    url=url,
                    success=False,
                    error=f"Unsupported content type: {content_type}",
                    depth=depth,
                )

            # Check if content matches interests
            if interests and not self._matches_interests(response.text, interests):
                return CrawlResult(
                    url=url,
                    success=False,
                    error="No interest match",
                    depth=depth,
                )

            # Extract content
            content = extract_content(
                response.text, url, status_code=response.status_code
            )
            links = extract_links(response.text, url)

            return CrawlResult(
                url=url,
                success=True,
                content=content,
                depth=depth,
                links_found=len(links),
            )

        except RequestException as e:
            return CrawlResult(
                url=url,
                success=False,
                error=str(e),
                depth=depth,
            )
        except Exception as e:
            return CrawlResult(
                url=url,
                success=False,
                error=f"Unexpected error: {str(e)}",
                depth=depth,
            )

    def _matches_interests(self, text: str, interests: List[Interest]) -> bool:
        """Check if text matches any of the given interests."""
        if not interests:
            return True
        return any(interest.matches(text) for interest in interests)

    def _get_next_links(
        self,
        content: ExtractedContent,
        current_url: str,
        interests: List[Interest],
    ) -> List[str]:
        """Get next links to crawl from content."""
        links = extract_links(content.text if content.text else "", current_url)
        # Also check the original content links
        for link in content.links:
            from urllib.parse import urljoin
            absolute = urljoin(current_url, link)
            if is_valid_url(absolute):
                links.append(normalize_url(absolute))
        return list(set(links))

    def get_stats(self) -> dict:
        """Get crawl statistics."""
        successful = sum(1 for r in self.results if r.success)
        failed = sum(1 for r in self.results if not r.success)
        return {
            "total_crawled": len(self.results),
            "successful": successful,
            "failed": failed,
            "unique_domains": len(self.domain_counts),
            "visited_urls": len(self.visited),
        }

    def reset(self) -> None:
        """Reset crawler state."""
        self.visited = set()
        self.domain_counts = {}
        self.results = []
