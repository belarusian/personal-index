"""Web crawler with configurable depth, politeness, and rate limiting."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

import requests

from personal_index.content_extractor import ContentExtractor
from personal_index.interest_store import InterestStore
from personal_index.models import CrawledPage
from personal_index.url_utils import (
    extract_all_urls,
    extract_domain,
    is_excluded_url,
    is_valid_url,
    normalize_url,
)


@dataclass
class CrawlerConfig:
    """Configuration for the web crawler."""

    max_depth: int = 3
    max_pages: int = 100
    delay: float = 1.0
    timeout: int = 10
    respect_robots: bool = True
    allowed_domains: List[str] = field(default_factory=list)
    user_agent: str = "PersonalIndex/0.1.0"


class Crawler:
    """Web crawler with depth control and politeness."""

    def __init__(
        self,
        config: Optional[CrawlerConfig] = None,
        interest_store: Optional[InterestStore] = None,
    ):
        self.config = config or CrawlerConfig()
        self.interest_store = interest_store
        self._visited: Set[str] = set()
        self._pages_crawled: int = 0
        self._results: List[CrawledPage] = []
        self._domain_delay: Dict[str, float] = {}
        self._extractor = ContentExtractor()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.config.user_agent})

    @property
    def pages_crawled(self) -> int:
        return self._pages_crawled

    @property
    def results(self) -> List[CrawledPage]:
        return list(self._results)

    def crawl(self, seed_urls: List[str], max_depth: int = None) -> List[CrawledPage]:
        """Start crawling from seed URLs."""
        depth = max_depth if max_depth is not None else self.config.max_depth
        self._visited = set()
        self._pages_crawled = 0
        self._results = []
        self._domain_delay = {}

        for url in seed_urls:
            normalized = normalize_url(url)
            if self._should_crawl(normalized):
                self._crawl_url(normalized, depth=0, max_depth=depth)

        return self._results

    def _crawl_url(self, url: str, depth: int, max_depth: int) -> None:
        """Crawl a single URL and follow links up to max_depth."""
        if not self._should_crawl(url):
            return

        self._visited.add(url)
        self._apply_delay(url)

        resp = self._fetch(url)
        if resp is None:
            return

        self._pages_crawled += 1
        page = self._extract_content(resp.text, url)
        page.depth = depth
        page.status_code = resp.status_code

        if self._filter_by_interests(page):
            self._results.append(page)

        if depth < max_depth:
            links = self._extract_links(resp.text, url)
            for link in links:
                normalized = normalize_url(link)
                if self._should_crawl(normalized):
                    self._crawl_url(normalized, depth + 1, max_depth)

    def _should_crawl(self, url: str) -> bool:
        """Determine if a URL should be crawled."""
        if not is_valid_url(url):
            return False
        if url in self._visited:
            return False
        if self._pages_crawled >= self.config.max_pages:
            return False
        if is_excluded_url(url):
            return False
        if self.config.allowed_domains:
            domain = self._get_domain(url)
            if not any(domain == d or domain.endswith("." + d) for d in self.config.allowed_domains):
                return False
        return True

    def _apply_delay(self, url: str) -> None:
        """Apply politeness delay between requests to same domain."""
        if self.config.delay <= 0:
            return
        domain = self._get_domain(url)
        now = time.time()
        last = self._domain_delay.get(domain, 0)
        wait = self.config.delay - (now - last)
        if wait > 0:
            time.sleep(wait)
        self._domain_delay[domain] = time.time()

    def _fetch(self, url: str) -> Optional[requests.Response]:
        """Fetch a URL and return response."""
        try:
            resp = self.session.get(url, timeout=self.config.timeout)
            if resp.status_code == 200:
                return resp
            return None
        except (requests.RequestException, Exception):
            return None

    def _extract_content(self, html: str, url: str) -> CrawledPage:
        """Extract content from HTML."""
        extracted = self._extractor.extract(html)
        return CrawledPage(
            url=url,
            title=extracted.title,
            content=extracted.text,
            meta_description=extracted.meta_description,
        )

    def _extract_links(self, html: str, base_url: str) -> List[str]:
        """Extract links from HTML."""
        return extract_all_urls(html, base_url)

    def _filter_by_interests(self, page: CrawledPage) -> bool:
        """Filter page by interests."""
        if not self.interest_store:
            return True
        text = f"{page.title} {page.content}"
        matches = self.interest_store.matches_any(text, page.url)
        if matches:
            page.matched_interests = [m.name for m in matches]
            page.relevance_score = self.interest_store.total_score(text)
            return True
        return False

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        return extract_domain(url)

    def close(self) -> None:
        """Close the crawler session."""
        self.session.close()


# Backwards-compatible alias
WebCrawler = Crawler
