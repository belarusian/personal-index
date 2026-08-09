"""Crawler package for personal-index."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from personal_index.models import CrawledPage, Interest, InterestType
from personal_index.interest_store import InterestStore


@dataclass
class CrawlerConfig:
    """Configuration for the web crawler."""
    max_depth: int = 3
    max_pages: int = 100
    delay: float = 1.0
    timeout: int = 10
    respect_robots: bool = True
    allowed_domains: list[str] = field(default_factory=list)
    blocked_extensions: list[str] = field(
        default_factory=lambda: [
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".ico",
            ".css", ".js", ".pdf", ".zip", ".tar", ".gz", ".rar",
            ".mp3", ".mp4", ".avi", ".mov", ".wmv", ".flv",
            ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
            ".exe", ".bin", ".dmg", ".iso",
        ]
    )

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CrawlerConfig":
        return cls(**{k: v for k, v in data.items()
                      if k in cls.__dataclass_fields__})


class Crawler:
    """Web crawler with depth control and politeness."""

    def __init__(self, config: Optional[CrawlerConfig] = None):
        self.config = config or CrawlerConfig()
        self._visited: set[str] = set()
        self._pages_crawled: int = 0
        self._results: list[CrawledPage] = []
        self.interest_store: Optional[InterestStore] = None
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "personal-index/0.1.0",
        })

    @property
    def pages_crawled(self) -> int:
        return self._pages_crawled

    @property
    def results(self) -> list[CrawledPage]:
        return list(self._results)

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc

    def _should_crawl(self, url: str) -> bool:
        """Check if URL should be crawled."""
        if not url:
            return False
        # Check scheme
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        # Check already visited
        if url in self._visited:
            return False
        # Check max pages
        if self._pages_crawled >= self.config.max_pages:
            return False
        # Check blocked extensions
        path = parsed.path.lower()
        for ext in self.config.blocked_extensions:
            if path.endswith(ext):
                return False
        # Check allowed domains
        if self.config.allowed_domains:
            domain = self._get_domain(url)
            if domain not in self.config.allowed_domains:
                return False
        return True

    def _fetch(self, url: str) -> Optional[requests.Response]:
        """Fetch a URL and return the response."""
        try:
            resp = self.session.get(
                url,
                timeout=self.config.timeout,
                allow_redirects=True,
            )
            if resp.status_code == 200:
                return resp
            return None
        except (requests.RequestException, Exception):
            return None

    def _extract_links(self, html: str, base_url: str) -> list[str]:
        """Extract links from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.startswith(("javascript:", "mailto:", "data:", "tel:")):
                continue
            from personal_index.utils.url_utils import resolve_relative_url
            resolved = resolve_relative_url(base_url, href)
            if resolved:
                links.append(resolved)
        return links

    def _extract_content(self, html: str, url: str) -> CrawledPage:
        """Extract content from HTML."""
        soup = BeautifulSoup(html, "html.parser")

        # Remove scripts and styles
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()

        # Extract title
        title = ""
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            title = title_tag.string.strip()

        # Extract meta description
        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag and meta_tag.get("content"):
            meta_desc = meta_tag["content"].strip()

        # Extract text
        text = soup.get_text(separator=" ")
        text = re.sub(r'\s+', ' ', text).strip()

        return CrawledPage(
            url=url,
            title=title,
            content=text,
            meta_description=meta_desc,
        )

    def _filter_by_interests(self, page: CrawledPage) -> bool:
        """Filter page by interests."""
        if not self.interest_store:
            return True
        interests = self.interest_store.list_all()
        matched = []
        for interest in interests:
            if interest.matches(page.content, page.url):
                matched.append(interest.name)
        page.matched_interests = matched
        return len(matched) > 0

    def crawl(self, seed_urls: list[str], max_depth: Optional[int] = None) -> list[CrawledPage]:
        """Crawl starting from seed URLs."""
        depth_limit = max_depth if max_depth is not None else self.config.max_depth
        to_crawl = [(url, 0) for url in seed_urls]

        while to_crawl:
            url, depth = to_crawl.pop(0)
            if not self._should_crawl(url):
                continue

            self._visited.add(url)
            resp = self._fetch(url)
            if resp is None:
                continue

            page = self._extract_content(resp.text, url)
            page.depth = depth
            page.status_code = resp.status_code

            if self._filter_by_interests(page):
                self._results.append(page)
                self._pages_crawled += 1

            # Extract and queue links
            if depth < depth_limit:
                links = self._extract_links(resp.text, url)
                for link in links:
                    if self._should_crawl(link):
                        to_crawl.append((link, depth + 1))

            # Politeness delay
            if self.config.delay > 0:
                time.sleep(self.config.delay)

        return list(self._results)

    def close(self):
        """Close the crawler session."""
        self.session.close()


class WebCrawler:
    """High-level web crawler interface for integration tests."""

    def __init__(self, config=None, content_filter=None):
        self.config = config
        self.content_filter = content_filter
        # Pass config to Crawler if it's a CrawlerConfig, otherwise use default
        from personal_index.crawler.__init__ import CrawlerConfig as _CC
        crawler_config = None
        if config is not None:
            if isinstance(config, _CC):
                crawler_config = config
            elif hasattr(config, 'crawler'):
                # AppConfig has a .crawler attribute
                crawler_config = config.crawler
            elif hasattr(config, 'max_depth'):
                # It's some config-like object, try to use it directly
                crawler_config = config
        self.crawler = Crawler(config=crawler_config)
        self.session = self.crawler.session

    def crawl(self, seed_urls: list[str], max_depth: int = 3) -> list:
        """Crawl starting from seed URLs and return Page objects."""
        pages = self.crawler.crawl(seed_urls, max_depth=max_depth)
        # Convert CrawledPage to Page objects
        from personal_index.models import Page
        result = []
        for page in pages:
            p = Page(
                url=page.url,
                title=page.title,
                content=page.content,
                meta_description=page.meta_description,
                matched_interests=page.matched_interests,
            )
            result.append(p)
        return result

    def close(self):
        """Close the crawler session."""
        self.crawler.close()
