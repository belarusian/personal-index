"""Web crawler with configurable depth, politeness, and rate limiting."""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from personal_index.interest_store import InterestStore
from personal_index.models import CrawledPage, Interest

logger = logging.getLogger(__name__)


@dataclass
class CrawlerConfig:
    """Configuration for the web crawler."""

    max_depth: int = 3
    max_pages: int = 100
    delay: float = 1.0  # seconds between requests to same domain
    timeout: int = 10  # seconds
    user_agent: str = "personal-index/0.1.0"
    respect_robots: bool = True
    allowed_domains: list[str] = field(default_factory=list)
    blocked_extensions: list[str] = field(
        default_factory=lambda: [
            ".jpg", ".jpeg", ".png", ".gif", ".pdf",
            ".zip", ".tar", ".gz", ".mp3", ".mp4",
            ".avi", ".mov", ".wmv", ".exe", ".doc",
            ".docx", ".xls", ".xlsx",
        ]
    )


class Crawler:
    """Web crawler that respects politeness and rate limits."""

    def __init__(
        self,
        config: Optional[CrawlerConfig] = None,
        interest_store: Optional[InterestStore] = None,
    ):
        self.config = config or CrawlerConfig()
        self.interest_store = interest_store
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.config.user_agent,
        })
        self._domain_last_visit: dict[str, float] = {}
        self._visited: set[str] = set()
        self._results: list[CrawledPage] = []
        self._pages_crawled: int = 0

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        return urlparse(url).netloc

    def _should_crawl(self, url: str) -> bool:
        """Check if URL should be crawled."""
        if url in self._visited:
            return False
        if self._pages_crawled >= self.config.max_pages:
            return False

        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False

        # Check blocked extensions
        path_lower = parsed.path.lower()
        for ext in self.config.blocked_extensions:
            if path_lower.endswith(ext):
                return False

        # Check allowed domains
        if self.config.allowed_domains:
            domain = parsed.netloc
            if not any(domain.endswith(d) for d in self.config.allowed_domains):
                return False

        return True

    def _rate_limit(self, url: str) -> None:
        """Apply rate limiting per domain."""
        domain = self._get_domain(url)
        now = time.time()
        last_visit = self._domain_last_visit.get(domain, 0)
        wait_time = self.config.delay - (now - last_visit)
        if wait_time > 0:
            time.sleep(wait_time)
        self._domain_last_visit[domain] = time.time()

    def _fetch(self, url: str) -> Optional[requests.Response]:
        """Fetch a URL with rate limiting."""
        self._rate_limit(url)
        try:
            response = self.session.get(
                url,
                timeout=self.config.timeout,
                allow_redirects=True,
            )
            if response.status_code == 200:
                return response
            logger.debug(f"Status {response.status_code} for {url}")
            return None
        except requests.RequestException as e:
            logger.debug(f"Error fetching {url}: {e}")
            return None

    def _extract_links(self, html: str, base_url: str) -> list[str]:
        """Extract all links from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(base_url, href)
            # Normalize URL
            parsed = urlparse(full_url)
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if normalized and self._should_crawl(normalized):
                links.append(normalized)
        return links

    def _extract_content(self, html: str, url: str) -> CrawledPage:
        """Extract content from HTML."""
        soup = BeautifulSoup(html, "html.parser")

        title = ""
        if soup.title:
            title = soup.title.string.strip()

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        content = soup.get_text(separator=" ", strip=True)
        # Limit content length
        content = content[:50000]

        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag and meta_tag.get("content"):
            meta_desc = meta_tag["content"]

        return CrawledPage(
            url=url,
            title=title,
            content=content,
            meta_description=meta_desc,
            status_code=200,
        )

    def _filter_by_interests(self, page: CrawledPage) -> bool:
        """Check if page matches any interests."""
        if not self.interest_store:
            return True  # No filter if no interest store

        text = f"{page.title} {page.content} {page.meta_description}"
        matching = self.interest_store.matches_any(text, page.url)
        if matching:
            page.matched_interests = [m.name for m in matching]
            page.relevance_score = self.interest_store.total_score(text, page.url)
            return True
        return False

    def crawl(self, seed_urls: list[str]) -> list[CrawledPage]:
        """Crawl starting from seed URLs."""
        self._visited.clear()
        self._results.clear()
        self._pages_crawled = 0

        queue: deque[tuple[str, int, Optional[str]]] = deque()
        for url in seed_urls:
            if self._should_crawl(url):
                queue.append((url, 0, None))
                self._visited.add(url)

        while queue:
            if self._pages_crawled >= self.config.max_pages:
                break

            url, depth, parent_url = queue.popleft()

            response = self._fetch(url)
            if not response:
                continue

            page = self._extract_content(response.text, url)
            page.depth = depth
            page.parent_url = parent_url
            self._pages_crawled += 1

            if self._filter_by_interests(page):
                self._results.append(page)

            # Extract and queue links if within depth
            if depth < self.config.max_depth:
                links = self._extract_links(response.text, url)
                for link in links:
                    if link not in self._visited:
                        self._visited.add(link)
                        queue.append((link, depth + 1, url))

        return self._results

    @property
    def pages_crawled(self) -> int:
        """Return number of pages crawled."""
        return self._pages_crawled

    @property
    def results(self) -> list[CrawledPage]:
        """Return filtered results."""
        return self._results
