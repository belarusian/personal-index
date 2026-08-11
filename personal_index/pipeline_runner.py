"""Pipeline runner that orchestrates the full crawl→extract→filter→score→tag→index pipeline."""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from personal_index.config.pipeline_config import PipelineConfig
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer, ScoreWeights
from personal_index.crawler.main import Crawler, CrawlerConfig
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage
from personal_index.tags import TagStore

logger = logging.getLogger(__name__)


@dataclass
class PipelineStats:
    """Statistics from a pipeline run."""

    pages_crawled: int = 0
    pages_extracted: int = 0
    pages_filtered_in: int = 0
    pages_filtered_out: int = 0
    pages_scored: int = 0
    pages_tagged: int = 0
    pages_indexed: int = 0
    errors: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    tags_applied: int = 0
    interests_matched: int = 0

    def summary(self) -> str:
        """Return a human-readable summary of pipeline stats."""
        lines = [
            "Pipeline Summary",
            "-" * 40,
            f"Crawled:      {self.pages_crawled}",
            f"Extracted:    {self.pages_extracted}",
            f"Filtered in:  {self.pages_filtered_in}",
            f"Filtered out: {self.pages_filtered_out}",
            f"Scored:       {self.pages_scored}",
            f"Tagged:       {self.pages_tagged}",
            f"Tags applied: {self.tags_applied}",
            f"Indexed:      {self.pages_indexed}",
            f"Errors:       {len(self.errors)}",
            f"Time:         {self.elapsed_seconds:.1f}s",
        ]
        return "\n".join(lines)


class PipelineRunner:
    """Orchestrates the full pipeline: crawl → extract → filter → score → tag → index.

    This is the main entry point for running the complete pipeline.
    It manages all components and coordinates data flow between stages.
    """

    def __init__(
        self,
        data_dir: str = ".personal_index",
        pipeline_config: PipelineConfig | None = None,
        progress_callback: Callable | None = None,
    ):
        self.data_dir = data_dir
        self.pipeline_config = pipeline_config or PipelineConfig()
        self._progress_callback = progress_callback

        # Initialize stores
        self._interest_store = InterestStore(
            store_path=os.path.join(data_dir, "interests.json")
        )
        self._tag_store = TagStore(
            store_path=os.path.join(data_dir, "tags.json")
        )
        self._search_index = SearchIndex(
            db_path=os.path.join(data_dir, "search_index.json")
        )

        # Initialize processing components
        self._filter = ContentFilter(
            config=FilterConfig(
                min_content_length=self.pipeline_config.min_content_length,
                min_title_length=3,
                blocked_domains=[],
                require_interest_match=False,
            ),
            interest_store=self._interest_store,
        )
        self._scorer = ContentScorer(weights=ScoreWeights())

        # Initialize crawler
        self._crawler = Crawler(
            config=CrawlerConfig(
                max_depth=self.pipeline_config.max_depth,
                max_pages=self.pipeline_config.max_pages,
                delay=self.pipeline_config.politeness_delay,
                timeout=self.pipeline_config.crawl_timeout,
            ),
            interest_store=self._interest_store,
        )

        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        for subdir in ["cache", "archive", "backups"]:
            os.makedirs(os.path.join(data_dir, subdir), exist_ok=True)

    def run(self, seed_urls: list[str], max_depth: int | None = None) -> PipelineStats:
        """Run the full pipeline on the given seed URLs.

        Args:
            seed_urls: List of URLs to start crawling from.
            max_depth: Override max crawl depth.

        Returns:
            PipelineStats with results from each stage.
        """
        stats = PipelineStats()
        start_time = time.time()

        try:
            # Stage 1: Crawl
            logger.info("Stage 1/6: Crawling %d seed URLs", len(seed_urls))
            pages = self._crawl_stage(seed_urls, stats, max_depth)

            # Stage 2: Extract
            logger.info("Stage 2/6: Extracting content from %d pages", len(pages))
            pages = self._extract_stage(pages, stats)

            # Stage 3: Filter
            logger.info("Stage 3/6: Filtering %d pages", len(pages))
            pages = self._filter_stage(pages, stats)

            # Stage 4: Score
            logger.info("Stage 4/6: Scoring %d pages", len(pages))
            pages = self._score_stage(pages, stats)

            # Stage 5: Tag
            logger.info("Stage 5/6: Tagging %d pages", len(pages))
            pages = self._tag_stage(pages, stats)

            # Stage 6: Index
            logger.info("Stage 6/6: Indexing %d pages", len(pages))
            self._index_stage(pages, stats)

        except Exception as e:
            stats.errors.append(f"Pipeline error: {e}")
            logger.error("Pipeline error: %s", e)

        stats.elapsed_seconds = time.time() - start_time
        return stats

    def run_from_files(self, file_paths: list[str]) -> PipelineStats:
        """Run the pipeline on local files instead of URLs.

        Args:
            file_paths: List of file paths to process.

        Returns:
            PipelineStats with results from each stage.
        """
        stats = PipelineStats()
        start_time = time.time()

        try:
            # Stage 1: Read files (replaces crawl)
            pages = self._read_files_stage(file_paths, stats)

            # Stage 2: Extract (files are already extracted, just normalize)
            pages = self._extract_stage(pages, stats)

            # Stage 3: Filter
            pages = self._filter_stage(pages, stats)

            # Stage 4: Score
            pages = self._score_stage(pages, stats)

            # Stage 5: Tag
            pages = self._tag_stage(pages, stats)

            # Stage 6: Index
            self._index_stage(pages, stats)

        except Exception as e:
            stats.errors.append(f"Pipeline error: {e}")
            logger.error("Pipeline error: %s", e)

        stats.elapsed_seconds = time.time() - start_time
        return stats

    def _crawl_stage(
        self, seed_urls: list[str], stats: PipelineStats, max_depth: int | None = None
    ) -> list[CrawledPage]:
        """Stage 1: Crawl URLs."""
        try:
            pages = self._crawler.crawl(seed_urls, max_depth=max_depth)
            stats.pages_crawled = len(pages)
            if self._progress_callback:
                self._progress_callback("crawl", stats.pages_crawled)
            return pages
        except Exception as e:
            stats.errors.append(f"Crawl error: {e}")
            return []

    def _read_files_stage(
        self, file_paths: list[str], stats: PipelineStats
    ) -> list[CrawledPage]:
        """Read local files and convert to CrawledPage objects."""
        pages = []
        for fp in file_paths:
            try:
                with open(fp, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                from pathlib import Path
                p = Path(fp)
                page = CrawledPage(
                    url=f"file://{os.path.abspath(fp)}",
                    title=p.stem,
                    content=content,
                    meta_description=content[:200],
                )
                pages.append(page)
            except Exception as e:
                stats.errors.append(f"File read error {fp}: {e}")
        stats.pages_crawled = len(pages)
        if self._progress_callback:
            self._progress_callback("crawl", stats.pages_crawled)
        return pages

    def _extract_stage(
        self, pages: list[CrawledPage], stats: PipelineStats
    ) -> list[CrawledPage]:
        """Stage 2: Extract content (pages already have content from crawl)."""
        # Content is already extracted by the crawler
        extracted = [p for p in pages if p.content]
        stats.pages_extracted = len(extracted)
        if self._progress_callback:
            self._progress_callback("extract", stats.pages_extracted)
        return extracted

    def _filter_stage(
        self, pages: list[CrawledPage], stats: PipelineStats
    ) -> list[CrawledPage]:
        """Stage 3: Filter pages."""
        included = self._filter.filter_pages(pages)
        stats.pages_filtered_in = len(included)
        stats.pages_filtered_out = len(pages) - len(included)
        if self._progress_callback:
            self._progress_callback("filter", stats.pages_filtered_in)
        return included

    def _score_stage(
        self, pages: list[CrawledPage], stats: PipelineStats
    ) -> list[CrawledPage]:
        """Stage 4: Score pages."""
        for page in pages:
            text = f"{page.title} {page.content}"
            score = self._scorer.score(
                keyword_matches=len(page.matched_interests or []),
                total_keywords=max(len(self._interest_store.get_all_keywords()), 1),
                word_count=len(page.content.split()),
                domain_authority=0.5,
            )
            page.relevance_score = score.total
        stats.pages_scored = len(pages)
        if self._progress_callback:
            self._progress_callback("score", stats.pages_scored)
        return pages

    def _tag_stage(
        self, pages: list[CrawledPage], stats: PipelineStats
    ) -> list[CrawledPage]:
        """Stage 5: Tag pages based on interests."""
        total_tags = 0
        for page in pages:
            text = f"{page.title} {page.content}"
            matches = self._interest_store.matches_any(text, page.url)
            for interest in matches:
                self._tag_store.add_tag_to_page(page.url, interest.name)
                total_tags += 1
                if interest.name not in (page.matched_interests or []):
                    if page.matched_interests is None:
                        page.matched_interests = []
                    page.matched_interests.append(interest.name)
            # Add keyword-based tags
            from personal_index.keyword_extractor import extract_keywords
            keywords = extract_keywords(page.content, max_keywords=5)
            for kw in keywords:
                self._tag_store.add_tag_to_page(page.url, kw)
                total_tags += 1
        stats.pages_tagged = len(pages)
        stats.tags_applied = total_tags
        stats.interests_matched = sum(
            1 for p in pages if p.matched_interests
        )
        if self._progress_callback:
            self._progress_callback("tag", stats.pages_tagged)
        return pages

    def _index_stage(
        self, pages: list[CrawledPage], stats: PipelineStats
    ) -> None:
        """Stage 6: Index pages."""
        for page in pages:
            try:
                self._search_index.add_page(page)
            except Exception as e:
                stats.errors.append(f"Index error for {page.url}: {e}")
        stats.pages_indexed = self._search_index.get_page_count()
        self._search_index._save()
        self._tag_store._save()
        self._interest_store._save()
        if self._progress_callback:
            self._progress_callback("index", stats.pages_indexed)

    def get_stats(self) -> dict[str, Any]:
        """Get current pipeline statistics."""
        return {
            "indexed_pages": self._search_index.get_page_count(),
            "total_interests": len(self._interest_store.list_all()),
            "total_tags": self._tag_store.get_tag_count(),
            "tagged_pages": self._tag_store.get_tagged_page_count(),
        }

    def close(self) -> None:
        """Close all resources."""
        self._crawler.close()
        self._search_index.close()
        self._tag_store._save()
        self._interest_store._save()
