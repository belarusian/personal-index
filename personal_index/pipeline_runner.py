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
            )
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

    def run(self, seed_urls: list[str]) -> PipelineStats:
        """Run the full pipeline on the given seed URLs.

        Args:
            seed_urls: List of URLs to start crawling from.

        Returns:
            PipelineStats with results from each stage.
        """
        stats = PipelineStats()
        start_time = time.time()

        try:
            # Stage 1: Crawl
            logger.info("Stage 1/6: Crawling %d seed URLs", len(seed_urls))
            pages = self._crawl_stage(seed_urls, stats)

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
            logger.error("Pipeline failed: %s", e)
            stats.errors.append(f"Pipeline error: {e}")

        stats.elapsed_seconds = time.time() - start_time
        return stats

    def run_from_files(self, file_paths: list[str]) -> PipelineStats:
        """Run the pipeline on local files (skip crawl stage).

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

            # Stage 2: Extract (already done for local files)
            stats.pages_extracted = len(pages)

            # Stage 3: Filter
            pages = self._filter_stage(pages, stats)

            # Stage 4: Score
            pages = self._score_stage(pages, stats)

            # Stage 5: Tag
            pages = self._tag_stage(pages, stats)

            # Stage 6: Index
            self._index_stage(pages, stats)

        except Exception as e:
            logger.error("Pipeline failed: %s", e)
            stats.errors.append(f"Pipeline error: {e}")

        stats.elapsed_seconds = time.time() - start_time
        return stats

    def _crawl_stage(self, seed_urls: list[str], stats: PipelineStats) -> list[CrawledPage]:
        """Execute the crawl stage."""
        try:
            pages = self._crawler.crawl(seed_urls)
            stats.pages_crawled = len(pages)
            self._progress("crawl", len(pages), len(pages))
            return pages
        except Exception as e:
            stats.errors.append(f"Crawl error: {e}")
            return []

    def _extract_stage(self, pages: list[CrawledPage], stats: PipelineStats) -> list[CrawledPage]:
        """Execute the extract stage.

        Content is already extracted by the crawler, so this validates
        that content exists and is usable.
        """
        extracted = []
        for page in pages:
            if page.content and len(page.content.strip()) > 0:
                extracted.append(page)
                stats.pages_extracted += 1
            else:
                stats.pages_filtered_out += 1
        self._progress("extract", stats.pages_extracted, len(pages))
        return extracted

    def _filter_stage(self, pages: list[CrawledPage], stats: PipelineStats) -> list[CrawledPage]:
        """Execute the filter stage."""
        filtered = []
        for page in pages:
            if self._filter.should_include(page):
                filtered.append(page)
                stats.pages_filtered_in += 1
            else:
                stats.pages_filtered_out += 1
        self._progress("filter", stats.pages_filtered_in, len(pages))
        return filtered

    def _score_stage(self, pages: list[CrawledPage], stats: PipelineStats) -> list[CrawledPage]:
        """Execute the scoring stage."""
        scored = []
        interests = self._interest_store.list_all()

        for page in pages:
            word_count = len((page.content or "").split())
            keyword_matches = 0
            total_keywords = 0
            matched_interest_names = []

            for interest in interests:
                for kw in interest.keywords:
                    total_keywords += 1
                    if kw.lower() in (page.content or "").lower():
                        keyword_matches += 1
                        matched_interest_names.append(interest.name)

            score_result = self._scorer.score(
                keyword_matches=keyword_matches,
                total_keywords=max(total_keywords, 1),
                word_count=word_count,
                domain_authority=0.5,
            )
            score = score_result.total if hasattr(score_result, "total") else 0.0
            page.relevance_score = score
            page.matched_interests = matched_interest_names

            if score >= self.pipeline_config.min_score_threshold:
                scored.append(page)
                stats.pages_scored += 1
                if matched_interest_names:
                    stats.interests_matched += 1
            else:
                stats.pages_filtered_out += 1

        self._progress("score", stats.pages_scored, len(pages))
        return scored

    def _tag_stage(self, pages: list[CrawledPage], stats: PipelineStats) -> list[CrawledPage]:
        """Execute the tagging stage."""
        tagged_count = 0
        total_tags = 0

        for page in pages:
            tags = self._auto_tag(page)
            for tag_name in tags:
                self._tag_store.add_tag_to_page(page.url, tag_name)
                total_tags += 1
            if tags:
                tagged_count += 1

        stats.pages_tagged = tagged_count
        stats.tags_applied = total_tags
        self._progress("tag", tagged_count, len(pages))
        return pages

    def _index_stage(self, pages: list[CrawledPage], stats: PipelineStats) -> None:
        """Execute the indexing stage."""
        for page in pages:
            try:
                self._search_index.add_page(page)
                stats.pages_indexed += 1
            except (OSError, ValueError) as e:
                stats.errors.append(f"Index error for {page.url}: {e}")
        self._progress("index", stats.pages_indexed, len(pages))

    def _read_files_stage(self, file_paths: list[str], stats: PipelineStats) -> list[CrawledPage]:
        """Read local files and convert to CrawledPage objects."""
        pages = []
        for filepath in file_paths:
            try:
                with open(filepath, "r", errors="replace") as f:
                    content = f.read()
                page = CrawledPage(
                    url=filepath,
                    title=os.path.basename(filepath),
                    content=content,
                )
                pages.append(page)
                stats.pages_crawled += 1
            except (OSError, ValueError) as e:
                stats.errors.append(f"Read error for {filepath}: {e}")
        return pages

    def _auto_tag(self, page: CrawledPage) -> list[str]:
        """Auto-generate tags for a page based on content and interests."""
        tags = set()

        # Tag by interest matches
        if page.matched_interests:
            for interest_name in page.matched_interests:
                tags.add(interest_name)

        # Tag by URL pattern heuristics
        if page.url:
            url_lower = page.url.lower()
            if "blog" in url_lower:
                tags.add("blog")
            if "api" in url_lower:
                tags.add("api")
            if "docs" in url_lower or "documentation" in url_lower:
                tags.add("documentation")
            if "github" in url_lower:
                tags.add("github")

        return list(tags)

    def _progress(self, stage: str, current: int, total: int) -> None:
        """Report progress if callback is set."""
        if self._progress_callback:
            self._progress_callback(stage, current, total)

    def get_stats(self) -> dict[str, Any]:
        """Get current pipeline statistics."""
        return {
            "indexed_pages": self._search_index.get_page_count(),
            "total_interests": len(self._interest_store.list_all()),
            "total_tags": self._tag_store.get_tag_count(),
            "tagged_pages": len(self._tag_store._page_tags),
        }

    def close(self) -> None:
        """Close all resources."""
        self._crawler.close()
        self._search_index.close()
