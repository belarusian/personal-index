"""Pipeline orchestration module for personal-index.

Wires together all pipeline stages: crawl → extract → filter → score → tag → index → search.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

from personal_index.content_extractor import ContentExtractor
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer, ScoreWeights
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, PipelineStats
from personal_index.scraper import HTMLScraper, ScraperConfig
from personal_index.tags import TagStore

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for the full pipeline."""

    # Crawl settings
    max_depth: int = 3
    max_pages: int = 100
    timeout: int = 30
    politeness_delay: float = 1.0

    # Filter settings
    min_content_length: int = 100
    max_content_length: int = 100000
    min_title_length: int = 3
    require_interest_match: bool = True
    blocked_domains: list[str] = field(default_factory=list)

    # Score settings
    min_score_threshold: float = 0.0
    score_weights: ScoreWeights = field(default_factory=ScoreWeights)

    # Tag settings
    auto_tag: bool = True
    tag_by_interest: bool = True
    tag_by_url_pattern: bool = True

    # Index settings
    persist_index: bool = True

    # Step enable/disable
    enabled_steps: list[str] = field(default_factory=lambda: [
        "crawl", "extract", "filter", "score", "tag", "index", "search"
    ])

    def is_step_enabled(self, step: str) -> bool:
        """Check if a pipeline step is enabled."""
        return step in self.enabled_steps

    @classmethod
    def from_dict(cls, data: dict) -> PipelineConfig:
        """Create PipelineConfig from a dictionary."""
        config = cls()
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config




@dataclass
class PipelineResult:
    """Result from executing a pipeline step."""
    success: bool = True
    data: dict = field(default_factory=dict)
    error: str = ""
    step_name: str = ""


class PipelineStep:
    """A single step in a content processing pipeline."""

    def __init__(self, name: str, handler: callable, enabled: bool = True, on_error: str = "raise"):
        self.name = name
        self.handler = handler
        self.enabled = enabled
        self.on_error = on_error

    def execute(self, data: dict) -> dict:
        """Execute this step on the data."""
        if not self.enabled:
            return data
        try:
            return self.handler(data)
        except Exception as e:
            if self.on_error == "continue":
                return data
            elif self.on_error == "skip":
                return data
            else:
                raise


class ContentPipeline:
    """Generic content processing pipeline used by PersonalIndexApp.

    Provides add_step(), run(), step_count, and enabled_steps interface.
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self._steps: list[tuple[str, callable, str]] = []

    def add_step(self, name: str, func: callable, on_error: str = "raise") -> None:
        """Add a processing step to the pipeline."""
        self._steps.append((name, func, on_error))

    @property
    def step_count(self) -> int:
        """Number of steps in the pipeline."""
        return len(self._steps)

    @property
    def enabled_steps(self) -> list[str]:
        """List of enabled step names."""
        return [name for name, _, _ in self._steps]

    def run(self, data: dict) -> dict:
        """Run all pipeline steps on the data dict."""
        for name, func, on_error in self._steps:
            try:
                data = func(data)
            except Exception as e:
                if on_error == "continue":
                    pass
                elif on_error == "skip":
                    pass
                else:
                    raise
        return data


class Pipeline:
    """Full pipeline orchestrator: crawl → extract → filter → score → tag → index → search.

    This class wires together all individual components into a cohesive
    pipeline that processes web content end-to-end.
    """

    def __init__(
        self,
        data_dir: str = ".personal_index",
        config: PipelineConfig | None = None,
    ):
        self.data_dir = data_dir
        self.config = config or PipelineConfig()

        # Initialize components
        self._ensure_dirs()

        self.interest_store = InterestStore(
            store_path=os.path.join(data_dir, "interests.json")
        )
        self.tag_store = TagStore(store_path=os.path.join(data_dir, "tags.json"))
        self.search_index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        self.extractor = ContentExtractor()
        self.scraper = HTMLScraper()

        filter_config = FilterConfig(
            min_content_length=self.config.min_content_length,
            max_content_length=self.config.max_content_length,
            min_title_length=self.config.min_title_length,
            require_interest_match=self.config.require_interest_match,
            blocked_domains=self.config.blocked_domains,
        )
        self.content_filter = ContentFilter(
            config=filter_config,
            interest_store=self.interest_store,
        )
        self.scorer = ContentScorer(weights=self.config.score_weights)

    def _ensure_dirs(self) -> None:
        """Ensure data directory structure exists."""
        for subdir in ["", "cache", "archive", "backups"]:
            os.makedirs(os.path.join(self.data_dir, subdir), exist_ok=True)

    def run(
        self,
        seed_urls: list[str],
        callback: Any = None,
    ) -> PipelineStats:
        """Run the full pipeline on seed URLs.

        Args:
            seed_urls: List of URLs to start crawling from.
            callback: Optional callback for progress updates.

        Returns:
            PipelineStats with results summary.
        """
        stats = PipelineStats()
        start_time = time.time()

        logger.info("Starting pipeline with %d seed URLs", len(seed_urls))

        # Step 1: Crawl
        if self.config.is_step_enabled("crawl"):
            pages = self._crawl_step(seed_urls, stats, callback)
        else:
            pages = []
            logger.info("Crawl step disabled")

        # Step 2: Extract
        if self.config.is_step_enabled("extract") and pages:
            pages = self._extract_step(pages, stats, callback)

        # Step 3: Filter
        if self.config.is_step_enabled("filter") and pages:
            pages = self._filter_step(pages, stats, callback)

        # Step 4: Score
        if self.config.is_step_enabled("score") and pages:
            pages = self._score_step(pages, stats, callback)

        # Step 5: Tag
        if self.config.is_step_enabled("tag") and pages:
            self._tag_step(pages, stats, callback)

        # Step 6: Index
        if self.config.is_step_enabled("index") and pages:
            self._index_step(pages, stats, callback)

        stats.elapsed_seconds = time.time() - start_time
        logger.info("Pipeline complete: %s", stats.summary())
        return stats

    def _crawl_step(
        self,
        seed_urls: list[str],
        stats: PipelineStats,
        callback: Any = None,
    ) -> list[CrawledPage]:
        """Crawl step: fetch pages from seed URLs."""
        logger.info("Step 1/6: Crawling %d seed URLs", len(seed_urls))
        pages: list[CrawledPage] = []

        for i, url in enumerate(seed_urls):
            try:
                page = self._fetch_page(url)
                if page:
                    pages.append(page)
                    stats.pages_crawled += 1
            except Exception as e:
                logger.warning("Failed to crawl %s: %s", url, e)
                stats.errors.append(f"Crawl error for {url}: {e}")
            if callback:
                callback("crawl", i + 1, len(seed_urls))

        logger.info("  Crawled %d pages", stats.pages_crawled)
        return pages

    def _fetch_page(self, url: str) -> CrawledPage | None:
        """Fetch a single page. Uses requests for HTTP URLs, reads files for file:// URLs."""
        if url.startswith("file://"):
            filepath = url[7:]
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                return CrawledPage(
                    url=url,
                    title=os.path.basename(filepath),
                    content=content,
                    status_code=200,
                )
            return None

        try:
            import urllib.request
            import ssl

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "personal-index/0.1.0"},
            )
            with urllib.request.urlopen(req, timeout=self.config.timeout, context=ctx) as resp:
                html = resp.read().decode("utf-8", errors="replace")
                return CrawledPage(
                    url=url,
                    title="",
                    content=html,
                    status_code=resp.status,
                    raw_html=html,
                )
        except Exception as e:
            logger.warning("Failed to fetch %s: %s", url, e)
            return None

    def _extract_step(
        self,
        pages: list[CrawledPage],
        stats: PipelineStats,
        callback: Any = None,
    ) -> list[CrawledPage]:
        """Extract step: parse HTML and extract meaningful content."""
        logger.info("Step 2/6: Extracting content from %d pages", len(pages))
        extracted = 0

        for i, page in enumerate(pages):
            if page.raw_html:
                extracted = self.extractor.extract(page.raw_html)
                page.title = extracted.title or page.title
                page.content = extracted.text
                page.word_count = extracted.word_count
                stats.pages_extracted += 1
            elif page.content and len(page.content) > 500:
                # Assume it's already raw HTML if very long
                extracted = self.extractor.extract(page.content)
                if extracted.text:
                    page.title = extracted.title or page.title
                    page.content = extracted.text
                    page.word_count = extracted.word_count
                    stats.pages_extracted += 1
                else:
                    stats.pages_extracted += 1
            else:
                # Plain text content, already extracted
                stats.pages_extracted += 1

            if callback:
                callback("extract", i + 1, len(pages))

        logger.info("  Extracted content from %d pages", stats.pages_extracted)
        return pages

    def _filter_step(
        self,
        pages: list[CrawledPage],
        stats: PipelineStats,
        callback: Any = None,
    ) -> list[CrawledPage]:
        """Filter step: remove pages that don't meet criteria."""
        logger.info("Step 3/6: Filtering %d pages", len(pages))
        filtered_pages = []

        for i, page in enumerate(pages):
            if self.content_filter.should_include(page):
                filtered_pages.append(page)
                stats.pages_passed_filter += 1
            else:
                stats.pages_filtered_out += 1
            if callback:
                callback("filter", i + 1, len(pages))

        logger.info("  %d pages passed filter, %d filtered out",
                     stats.pages_passed_filter, stats.pages_filtered_out)
        return filtered_pages

    def _score_step(
        self,
        pages: list[CrawledPage],
        stats: PipelineStats,
        callback: Any = None,
    ) -> list[CrawledPage]:
        """Score step: calculate relevance scores."""
        logger.info("Step 4/6: Scoring %d pages", len(pages))
        scored_pages = []

        for i, page in enumerate(pages):
            score_result = self.scorer.score_page(page, self.interest_store)
            score = score_result.total if hasattr(score_result, "total") else score_result
            page.relevance_score = score

            if score >= self.config.min_score_threshold:
                scored_pages.append(page)
                stats.pages_scored += 1
            else:
                stats.pages_filtered_out += 1

            if callback:
                callback("score", i + 1, len(pages))

        logger.info("  %d pages scored above threshold", stats.pages_scored)
        return scored_pages

    def _tag_step(
        self,
        pages: list[CrawledPage],
        stats: PipelineStats,
        callback: Any = None,
    ) -> None:
        """Tag step: auto-generate tags for pages."""
        logger.info("Step 5/6: Tagging %d pages", len(pages))
        total_tags = 0

        for i, page in enumerate(pages):
            tags = self._auto_tag(page)
            for tag_name in tags:
                self.tag_store.add_tag_to_page(page.url, tag_name)
                total_tags += 1
            if tags:
                stats.pages_tagged += 1
            if callback:
                callback("tag", i + 1, len(pages))

        stats.tags_applied = total_tags
        logger.info("  Tagged %d pages with %d total tags", stats.pages_tagged, total_tags)

    def _index_step(
        self,
        pages: list[CrawledPage],
        stats: PipelineStats,
        callback: Any = None,
    ) -> None:
        """Index step: add pages to search index."""
        logger.info("Step 6/6: Indexing %d pages", len(pages))

        for i, page in enumerate(pages):
            try:
                self.search_index.add_page(page)
                stats.pages_indexed += 1
            except (OSError, ValueError) as e:
                logger.warning("Failed to index %s: %s", page.url, e)
                stats.errors.append(f"Index error for {page.url}: {e}")
            if callback:
                callback("index", i + 1, len(pages))

        logger.info("  Indexed %d pages", stats.pages_indexed)

    def _auto_tag(self, page: CrawledPage) -> list[str]:
        """Auto-generate tags for a page."""
        tags = set()

        if self.config.tag_by_interest:
            for interest in self.interest_store.list_all():
                if interest.matches(page.content or "", page.url):
                    tags.add(interest.name)

        if self.config.tag_by_url_pattern and page.url:
            url_lower = page.url.lower()
            if "blog" in url_lower:
                tags.add("blog")
            if "api" in url_lower:
                tags.add("api")
            if "docs" in url_lower or "documentation" in url_lower:
                tags.add("documentation")
            if "github" in url_lower:
                tags.add("github")

        if page.matched_interests:
            for mi in page.matched_interests:
                tags.add(mi)

        return list(tags)

    def search(self, query: str, limit: int = 20, tag: str | None = None) -> list:
        """Search the index.

        Args:
            query: Search query string.
            limit: Maximum results to return.
            tag: Optional tag filter.

        Returns:
            List of search results.
        """
        if tag:
            tagged_urls = self.tag_store.get_pages_for_tag(tag)
            results = self.search_index.search(query, limit=limit)
            return [r for r in results if r.url in tagged_urls]
        return self.search_index.search(query, limit=limit)

    def add_page_directly(self, page: CrawledPage) -> bool:
        """Add a page directly through the pipeline (skip crawl)."""
        # Extract content from raw HTML if available
        if page.raw_html and (not page.title or not page.content):
            extracted = self.extractor.extract(page.raw_html)
            if extracted.title:
                page.title = extracted.title
            if extracted.text:
                page.content = extracted.text
            page.word_count = extracted.word_count

        if not page.content:
            return False

        if not self.content_filter.should_include(page):
            return False

        score_result = self.scorer.score_page(page, self.interest_store)
        score = score_result.total if hasattr(score_result, "total") else score_result
        page.relevance_score = score

        if score < self.config.min_score_threshold:
            return False

        tags = self._auto_tag(page)
        for tag_name in tags:
            self.tag_store.add_tag_to_page(page.url, tag_name)

        try:
            self.search_index.add_page(page)
            return True
        except (OSError, ValueError):
            return False

    def get_stats(self) -> dict:
        """Get pipeline statistics."""
        return {
            "indexed_pages": self.search_index.get_page_count(),
            "total_interests": len(self.interest_store.list_all()),
            "total_tags": self.tag_store.get_tag_count(),
            "tagged_pages": self.tag_store.get_tagged_page_count(),
        }
