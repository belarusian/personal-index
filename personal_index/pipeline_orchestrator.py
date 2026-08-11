"""Pipeline orchestrator - ties all components together end-to-end.

This module provides the unified pipeline that connects:
  crawl → extract → filter → score → tag → index → search

Usage:
    from personal_index.pipeline_orchestrator import PipelineOrchestrator

    orchestrator = PipelineOrchestrator(data_dir=".personal_index")
    stats = orchestrator.run(["https://example.com"])
    results = orchestrator.search("python")
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

from personal_index.config.pipeline_config import PipelineConfig
from personal_index.content_extractor import ContentExtractor
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer, ScoreWeights
from personal_index.crawler.main import Crawler, CrawlerConfig
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, PipelineStats
from personal_index.tags import TagStore

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result from a pipeline execution."""
    stats: PipelineStats = field(default_factory=PipelineStats)
    pages: list[CrawledPage] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    success: bool = True

    def summary(self) -> str:
        """Return human-readable summary."""
        lines = [
            "Pipeline Result",
            "=" * 40,
            f"  Pages crawled:    {self.stats.pages_crawled}",
            f"  Pages extracted:  {self.stats.pages_extracted}",
            f"  Pages filtered:   {self.stats.pages_passed_filter}",
            f"  Pages scored:     {self.stats.pages_scored}",
            f"  Pages tagged:     {self.stats.pages_tagged}",
            f"  Pages indexed:    {self.stats.pages_indexed}",
            f"  Tags applied:     {self.stats.tags_applied}",
            f"  Errors:           {len(self.errors)}",
            f"  Time:             {self.stats.elapsed_seconds:.1f}s",
        ]
        return "\n".join(lines)


class PipelineOrchestrator:
    """Orchestrates the full content pipeline end-to-end.

    Manages all pipeline components and coordinates data flow
    between stages: crawl → extract → filter → score → tag → index.
    """

    def __init__(
        self,
        data_dir: str = ".personal_index",
        config: PipelineConfig | None = None,
        progress_callback: Any = None,
    ):
        self.data_dir = data_dir
        self.config = config or PipelineConfig()
        self.progress_callback = progress_callback

        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        for subdir in ["cache", "archive", "backups"]:
            os.makedirs(os.path.join(data_dir, subdir), exist_ok=True)

        # Initialize all pipeline components
        self.interest_store = InterestStore(
            store_path=os.path.join(data_dir, "interests.json")
        )
        self.tag_store = TagStore(store_path=os.path.join(data_dir, "tags.json"))
        self.search_index = SearchIndex(
            db_path=os.path.join(data_dir, "search_index.json")
        )
        self.content_extractor = ContentExtractor()
        self.content_scorer = ContentScorer(weights=ScoreWeights())

        filter_config = FilterConfig(
            min_content_length=self.config.min_content_length,
            require_interest_match=False,  # Allow pages without interest match
        )
        self.content_filter = ContentFilter(
            config=filter_config,
            interest_store=self.interest_store,
        )

        crawler_config = CrawlerConfig(
            max_depth=self.config.max_depth,
            max_pages=self.config.max_pages,
            timeout=30,
            delay=1.0,
        )
        self.crawler = Crawler(
            config=crawler_config,
            interest_store=self.interest_store,
        )

    def _emit_progress(self, stage: str, current: int, total: int) -> None:
        """Emit progress callback if configured."""
        if self.progress_callback:
            try:
                self.progress_callback(stage, current, total)
            except Exception:
                pass

    def run(self, seed_urls: list[str]) -> PipelineResult:
        """Run the full pipeline on seed URLs.

        Args:
            seed_urls: List of URLs to start crawling from.

        Returns:
            PipelineResult with stats and processed pages.
        """
        result = PipelineResult()
        start_time = time.time()

        try:
            # Stage 1: Crawl
            logger.info("Stage 1/6: Crawling %d seed URLs", len(seed_urls))
            self._emit_progress("crawl", 0, len(seed_urls))
            crawled_pages = self.crawler.crawl(seed_urls)
            result.stats.pages_crawled = len(crawled_pages)
            self._emit_progress("crawl", len(crawled_pages), len(crawled_pages))
            logger.info("Crawled %d pages", len(crawled_pages))

            # Stage 2: Extract (already done by crawler, but track it)
            result.stats.pages_extracted = len(crawled_pages)

            # Stage 3: Filter
            logger.info("Stage 3/6: Filtering %d pages", len(crawled_pages))
            self._emit_progress("filter", 0, len(crawled_pages))
            filtered_pages = []
            for i, page in enumerate(crawled_pages):
                if self.content_filter.should_include(page):
                    filtered_pages.append(page)
                    result.stats.pages_passed_filter += 1
                else:
                    result.stats.pages_filtered_out += 1
                self._emit_progress("filter", i + 1, len(crawled_pages))
            logger.info("Filtered to %d pages", len(filtered_pages))

            # Stage 4: Score
            logger.info("Stage 4/6: Scoring %d pages", len(filtered_pages))
            self._emit_progress("score", 0, len(filtered_pages))
            for i, page in enumerate(filtered_pages):
                score = self._score_page(page)
                page.relevance_score = score
                result.stats.pages_scored += 1
                self._emit_progress("score", i + 1, len(filtered_pages))

            # Stage 5: Tag
            logger.info("Stage 5/6: Tagging %d pages", len(filtered_pages))
            self._emit_progress("tag", 0, len(filtered_pages))
            for i, page in enumerate(filtered_pages):
                tags = self._tag_page(page)
                result.stats.pages_tagged += 1
                result.stats.tags_applied += len(tags)
                self._emit_progress("tag", i + 1, len(filtered_pages))

            # Stage 6: Index
            logger.info("Stage 6/6: Indexing %d pages", len(filtered_pages))
            self._emit_progress("index", 0, len(filtered_pages))
            for i, page in enumerate(filtered_pages):
                self.search_index.add_page(page)
                result.stats.pages_indexed += 1
                result.pages.append(page)
                self._emit_progress("index", i + 1, len(filtered_pages))

        except Exception as e:
            logger.error("Pipeline error: %s", e, exc_info=True)
            result.errors.append(str(e))
            result.success = False
        finally:
            result.stats.elapsed_seconds = time.time() - start_time

        return result

    def run_from_files(self, filepaths: list[str]) -> PipelineResult:
        """Run the pipeline on local files (skip crawl stage).

        Args:
            filepaths: List of local file paths to process.

        Returns:
            PipelineResult with stats and processed pages.
        """
        result = PipelineResult()
        start_time = time.time()

        try:
            # Stage 1: Read files (replaces crawl)
            logger.info("Stage 1/5: Reading %d files", len(filepaths))
            self._emit_progress("read", 0, len(filepaths))
            pages = []
            for i, filepath in enumerate(filepaths):
                page = self._read_file_as_page(filepath)
                if page:
                    pages.append(page)
                    result.stats.pages_crawled += 1
                self._emit_progress("read", i + 1, len(filepaths))
            logger.info("Read %d files", len(pages))

            result.stats.pages_extracted = len(pages)

            # Stage 2: Filter
            logger.info("Stage 2/5: Filtering %d pages", len(pages))
            self._emit_progress("filter", 0, len(pages))
            filtered_pages = []
            for i, page in enumerate(pages):
                if self.content_filter.should_include(page):
                    filtered_pages.append(page)
                    result.stats.pages_passed_filter += 1
                else:
                    result.stats.pages_filtered_out += 1
                self._emit_progress("filter", i + 1, len(pages))

            # Stage 3: Score
            logger.info("Stage 3/5: Scoring %d pages", len(filtered_pages))
            self._emit_progress("score", 0, len(filtered_pages))
            for i, page in enumerate(filtered_pages):
                score = self._score_page(page)
                page.relevance_score = score
                result.stats.pages_scored += 1
                self._emit_progress("score", i + 1, len(filtered_pages))

            # Stage 4: Tag
            logger.info("Stage 4/5: Tagging %d pages", len(filtered_pages))
            self._emit_progress("tag", 0, len(filtered_pages))
            for i, page in enumerate(filtered_pages):
                tags = self._tag_page(page)
                result.stats.pages_tagged += 1
                result.stats.tags_applied += len(tags)
                self._emit_progress("tag", i + 1, len(filtered_pages))

            # Stage 5: Index
            logger.info("Stage 5/5: Indexing %d pages", len(filtered_pages))
            self._emit_progress("index", 0, len(filtered_pages))
            for i, page in enumerate(filtered_pages):
                self.search_index.add_page(page)
                result.stats.pages_indexed += 1
                result.pages.append(page)
                self._emit_progress("index", i + 1, len(filtered_pages))

        except Exception as e:
            logger.error("Pipeline error: %s", e, exc_info=True)
            result.errors.append(str(e))
            result.success = False
        finally:
            result.stats.elapsed_seconds = time.time() - start_time

        return result

    def search(self, query: str, limit: int = 20) -> list[Any]:
        """Search the indexed content.

        Args:
            query: Search query string.
            limit: Maximum number of results.

        Returns:
            List of search results.
        """
        return self.search_index.search(query, limit=limit)

    def _score_page(self, page: CrawledPage) -> float:
        """Score a page based on content and interests."""
        word_count = len(page.content.split()) if page.content else 0
        keyword_matches = 0
        total_keywords = 0
        for interest in self.interest_store.list_all():
            for kw in interest.keywords:
                total_keywords += 1
                if kw.lower() in (page.content or "").lower():
                    keyword_matches += 1
                    if not page.matched_interests:
                        page.matched_interests = []
                    if interest.name not in page.matched_interests:
                        page.matched_interests.append(interest.name)

        if total_keywords == 0:
            return 0.5  # Neutral score when no interests configured

        score_result = self.content_scorer.score(
            keyword_matches=keyword_matches,
            total_keywords=total_keywords,
            word_count=word_count,
            domain_authority=0.5,
        )
        return score_result.total if hasattr(score_result, "total") else 0.0

    def _tag_page(self, page: CrawledPage) -> list[str]:
        """Auto-tag a page based on interests and keywords."""
        tags = []
        text = f"{page.title} {page.content}"

        # Interest-based tags
        matches = self.interest_store.matches_any(text, page.url)
        for interest in matches:
            self.tag_store.add_tag_to_page(page.url, interest.name)
            tags.append(interest.name)

        # Keyword-based tags
        from personal_index.keyword_extractor import extract_keywords
        keywords = extract_keywords(page.content or "", max_keywords=5)
        for kw in keywords:
            self.tag_store.add_tag_to_page(page.url, kw)
            tags.append(kw)

        return tags

    def _read_file_as_page(self, filepath: str) -> CrawledPage | None:
        """Read a local file and convert to CrawledPage."""
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            title = os.path.basename(filepath)
            if content.startswith("# "):
                title = content.split("\n")[0][2:].strip()

            return CrawledPage(
                url=f"file://{os.path.abspath(filepath)}",
                title=title,
                content=content,
                word_count=len(content.split()),
            )
        except (OSError, ValueError):
            return None

    def close(self) -> None:
        """Close all resources and persist state."""
        self.crawler.close()
        self.search_index.close()
        self.tag_store._save()
        self.interest_store._save()
