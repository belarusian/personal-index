"""Content crawler - crawl linked pages from saved items."""

from __future__ import annotations

import uuid
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class CrawlTaskStatus(str, Enum):
    """Status of a crawl task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CrawlResult:
    """Result of crawling a single page."""
    url: str
    title: str = ""
    content: str = ""
    meta_description: str = ""
    links: list[str] = field(default_factory=list)
    status_code: int = 0
    error: str = ""
    crawled_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)


@dataclass
class CrawlStats:
    """Statistics for a crawl operation."""
    total_pages: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    total_links_found: int = 0
    duration_seconds: float = 0.0

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)


@dataclass
class CrawlTask:
    """A task to crawl pages linked from a saved item."""
    source_url: str
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: CrawlTaskStatus = CrawlTaskStatus.PENDING
    max_depth: int = 2
    max_pages: int = 50
    delay: float = 0.5
    timeout: int = 10
    allowed_domains: list[str] = field(default_factory=list)
    blocked_domains: list[str] = field(default_factory=list)
    blocked_extensions: list[str] = field(
        default_factory=lambda: [
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".ico",
            ".css", ".js", ".pdf", ".zip", ".tar", ".gz", ".rar",
            ".mp3", ".mp4", ".avi", ".mov", ".wmv", ".flv",
            ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
            ".exe", ".bin", ".dmg", ".iso",
        ]
    )
    results: list[CrawlResult] = field(default_factory=list)
    stats: Optional[CrawlStats] = None
    error: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at: Optional[str] = None

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CrawlTask":
        return cls(
            **{k: v for k, v in data.items()
               if k in cls.__dataclass_fields__}
        )


class CrawlQueue:
    """Manages a queue of crawl tasks."""

    def __init__(self):
        self._tasks: dict[str, CrawlTask] = {}

    def add_task(self, task: CrawlTask) -> None:
        """Add a crawl task to the queue."""
        self._tasks[task.task_id] = task

    def get_next_pending(self) -> Optional[CrawlTask]:
        """Get the next pending task (FIFO)."""
        for task in self._tasks.values():
            if task.status == CrawlTaskStatus.PENDING:
                return task
        return None

    def complete_task(self, task_id: str) -> Optional[CrawlTask]:
        """Mark a task as completed."""
        if task_id in self._tasks:
            task = self._tasks[task_id]
            task.status = CrawlTaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc).isoformat()
            return task
        return None

    def fail_task(self, task_id: str, error: str = "") -> Optional[CrawlTask]:
        """Mark a task as failed."""
        if task_id in self._tasks:
            task = self._tasks[task_id]
            task.status = CrawlTaskStatus.FAILED
            task.error = error
            task.completed_at = datetime.now(timezone.utc).isoformat()
            return task
        return None

    def cancel_task(self, task_id: str) -> Optional[CrawlTask]:
        """Cancel a task."""
        if task_id in self._tasks:
            task = self._tasks[task_id]
            task.status = CrawlTaskStatus.CANCELLED
            task.completed_at = datetime.now(timezone.utc).isoformat()
            return task
        return None

    def get_task(self, task_id: str) -> Optional[CrawlTask]:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    @property
    def pending(self) -> list[CrawlTask]:
        return [t for t in self._tasks.values() if t.status == CrawlTaskStatus.PENDING]

    @property
    def pending_count(self) -> int:
        return len(self.pending)

    @property
    def completed_count(self) -> int:
        return sum(1 for t in self._tasks.values() if t.status == CrawlTaskStatus.COMPLETED)

    @property
    def failed_count(self) -> int:
        return sum(1 for t in self._tasks.values() if t.status == CrawlTaskStatus.FAILED)

    @property
    def all_tasks(self) -> list[CrawlTask]:
        return list(self._tasks.values())


class ContentCrawler:
    """Crawls linked pages from saved content items."""

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": "personal-index-crawler/0.1.0",
        })
        self._visited: set[str] = set()

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc

    def _should_crawl(self, url: str, task: CrawlTask) -> bool:
        """Check if a URL should be crawled."""
        if not url:
            return False
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        if url in self._visited:
            return False
        # Check blocked extensions
        path = parsed.path.lower()
        for ext in task.blocked_extensions:
            if path.endswith(ext):
                return False
        # Check blocked domains
        domain = self._get_domain(url)
        if domain in task.blocked_domains:
            return False
        # Check allowed domains
        if task.allowed_domains and domain not in task.allowed_domains:
            return False
        return True

    def _fetch_page(self, url: str, timeout: int = 10) -> Optional[requests.Response]:
        """Fetch a page and return the response."""
        try:
            resp = self.session.get(url, timeout=timeout, allow_redirects=True)
            if resp.status_code == 200:
                return resp
            return None
        except (requests.RequestException, Exception) as e:
            logger.debug(f"Failed to fetch {url}: {e}")
            return None

    def _extract_links(self, html: str, base_url: str) -> list[str]:
        """Extract links from HTML content."""
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.startswith(("javascript:", "mailto:", "data:", "tel:", "#")):
                continue
            resolved = urljoin(base_url, href)
            if resolved:
                links.append(resolved)
        return links

    def _extract_content(self, html: str, url: str) -> tuple[str, str, str]:
        """Extract title, content, and meta description from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()

        title = ""
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            title = title_tag.string.strip()

        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag and meta_tag.get("content"):
            meta_desc = meta_tag["content"].strip()

        text = soup.get_text(separator=" ")
        import re
        text = re.sub(r'\s+', ' ', text).strip()

        return title, text, meta_desc

    def crawl(self, task: CrawlTask) -> CrawlStats:
        """Execute a crawl task."""
        task.status = CrawlTaskStatus.RUNNING
        self._visited = set()
        stats = CrawlStats()
        start_time = time.time()

        # Start with the source URL
        to_crawl = [(task.source_url, 0)]

        while to_crawl and stats.total_pages < task.max_pages:
            url, depth = to_crawl.pop(0)

            if depth > task.max_depth:
                stats.skipped += 1
                continue

            if not self._should_crawl(url, task):
                stats.skipped += 1
                continue

            # Mark as visited before fetching
            self._visited.add(url)

            stats.total_pages += 1
            resp = self._fetch_page(url, task.timeout)

            if resp is None:
                stats.failed += 1
                result = CrawlResult(url=url, status_code=0, error="fetch_failed")
                task.results.append(result)
                continue

            title, content, meta_desc = self._extract_content(resp.text, url)
            links = self._extract_links(resp.text, url)

            stats.successful += 1
            stats.total_links_found += len(links)

            result = CrawlResult(
                url=url,
                title=title,
                content=content,
                meta_description=meta_desc,
                links=links,
                status_code=resp.status_code,
            )
            task.results.append(result)

            # Add new links to crawl queue
            if depth < task.max_depth:
                for link in links:
                    if link not in self._visited and self._should_crawl(link, task):
                        self._visited.add(link)
                        to_crawl.append((link, depth + 1))

            # Politeness delay
            time.sleep(task.delay)

        stats.duration_seconds = time.time() - start_time
        task.stats = stats
        task.status = CrawlTaskStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc).isoformat()

        return stats

    def crawl_from_saved_item(self, source_url: str, max_depth: int = 2,
                               max_pages: int = 50) -> CrawlStats:
        """Convenience method to crawl from a saved item URL."""
        task = CrawlTask(
            source_url=source_url,
            max_depth=max_depth,
            max_pages=max_pages,
        )
        return self.crawl(task)


class CrawlURLNormalizer:
    """Normalizes URLs for deduplication during crawling."""

    @staticmethod
    def normalize(url: str) -> str:
        """Normalize a URL for comparison."""
        parsed = urlparse(url)
        # Remove trailing slash from path (except root)
        path = parsed.path.rstrip("/") or "/"
        # Remove fragment
        # Sort query params for consistent comparison
        query = parsed.query
        return urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            parsed.params,
            query,
            "",  # Remove fragment
        ))

    @staticmethod
    def is_same_page(url1: str, url2: str) -> bool:
        """Check if two URLs point to the same page."""
        return CrawlURLNormalizer.normalize(url1) == CrawlURLNormalizer.normalize(url2)


def urlunparse(components):
    """Reconstruct URL from components."""
    from urllib.parse import urlunparse as _urlunparse
    return _urlunparse(components)
