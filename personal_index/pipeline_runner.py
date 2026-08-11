"""Pipeline runner that orchestrates the full crawl→extract→filter→score→tag→index pipeline."""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field

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

    def _emit_progress(self, stage: str, count: int, total: int = 0) -> None:
        """Emit progress update, handling different callback signatures."""
        if self._progress_callback is None:
            return
        import inspect
        sig = inspect.signature(self._progress_callback)
        params = list(sig.parameters.values())
        if len(params) >= 3:
            self._progress_callback(stage, count, total)
        else:
            self._progress_callback(stage, count)

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
            self._emit_progress("crawl", 0, len(seed_urls))
            crawled_pages = self._crawler.crawl(seed_urls, max_depth=max_depth)
            stats.pages_crawled = len(crawled_pages)
            self._emit_progress("crawl", stats.pages_crawled, len(seed_urls))
            logger.info("Crawled %d pages", stats.pages_crawled)

            # Stage 2: Extract (already done by crawler)
            stats.pages_extracted = stats.pages_crawled
            self._emit_progress("extract", stats.pages_extracted)
            logger.info("Extracted content from %d pages", stats.pages_extracted)

            # Stage 3: Filter
            logger.info("Stage 3/6: Filtering %d pages", len(crawled_pages))
            self._emit_progress("filter", 0, len(crawled_pages))
            filtered_pages = []
            for i, page in enumerate(crawled_pages):
                if self._filter.should_include(page):
                    filtered_pages.append(page)
                    stats.pages_filtered_in += 1
                else:
                    stats.pages_filtered_out += 1
                self._emit_progress("filter", i + 1, len(crawled_pages))
            logger.info("Filtered: %d in, %d out",
                        stats.pages_filtered_in, stats.pages_filtered_out)

            # Stage 4: Score
            logger.info("Stage 4/6: Scoring %d pages", len(filtered_pages))
            self._emit_progress("score", 0, len(filtered_pages))
            for i, page in enumerate(filtered_pages):
                score_result = self._scorer.score_page(page, interest_store=self._interest_store)
                page.relevance_score = score_result.total
                stats.pages_scored += 1
                self._emit_progress("score", i + 1, len(filtered_pages))
            logger.info("Scored %d pages", stats.pages_scored)

            # Stage 5: Tag
            logger.info("Stage 5/6: Tagging %d pages", len(filtered_pages))
            self._emit_progress("tag", 0, len(filtered_pages))
            for i, page in enumerate(filtered_pages):
                tags = self._auto_tag_page(page)
                stats.pages_tagged += 1
                stats.tags_applied += len(tags)
                if tags:
                    stats.interests_matched += 1
                self._emit_progress("tag", i + 1, len(filtered_pages))
            logger.info("Tagged %d pages with %d tags",
                        stats.pages_tagged, stats.tags_applied)

            # Stage 6: Index
            logger.info("Stage 6/6: Indexing %d pages", len(filtered_pages))
            self._emit_progress("index", 0, len(filtered_pages))
            for i, page in enumerate(filtered_pages):
                self._search_index.add_page(page)
                stats.pages_indexed += 1
                self._emit_progress("index", i + 1, len(filtered_pages))
            logger.info("Indexed %d pages", stats.pages_indexed)

        except (RuntimeError, OSError) as e:
            logger.error("Pipeline error: %s", e)
            stats.errors.append(str(e))
        finally:
            stats.elapsed_seconds = time.time() - start_time

        return stats

    def run_from_files(self, file_paths: list[str]) -> PipelineStats:
        """Run the pipeline on local files instead of crawling URLs.

        Args:
            file_paths: List of local file paths to process.

        Returns:
            PipelineStats with results from each stage.
        """
        stats = PipelineStats()
        start_time = time.time()

        try:
            # Stage 1: Read files (equivalent to crawl)
            logger.info("Stage 1/6: Reading %d files", len(file_paths))
            self._emit_progress("crawl", 0, len(file_paths))
            crawled_pages = []
            for i, filepath in enumerate(file_paths):
                try:
                    page = self._read_file_as_page(filepath)
                    if page:
                        crawled_pages.append(page)
                        stats.pages_crawled += 1
                except (RuntimeError, OSError) as e:
                    stats.errors.append(f"Error reading {filepath}: {e}")
                self._emit_progress("crawl", i + 1, len(file_paths))
            logger.info("Read %d files", stats.pages_crawled)

            # Stage 2: Extract (content already extracted from file)
            stats.pages_extracted = stats.pages_crawled
            self._emit_progress("extract", stats.pages_extracted)

            # Stage 3: Filter
            logger.info("Stage 3/6: Filtering %d pages", len(crawled_pages))
            self._emit_progress("filter", 0, len(crawled_pages))
            filtered_pages = []
            for i, page in enumerate(crawled_pages):
                if self._filter.should_include(page):
                    filtered_pages.append(page)
                    stats.pages_filtered_in += 1
                else:
                    stats.pages_filtered_out += 1
                self._emit_progress("filter", i + 1, len(crawled_pages))

            # Stage 4: Score
            logger.info("Stage 4/6: Scoring %d pages", len(filtered_pages))
            self._emit_progress("score", 0, len(filtered_pages))
            for i, page in enumerate(filtered_pages):
                score_result = self._scorer.score_page(page, interest_store=self._interest_store)
                page.relevance_score = score_result.total
                stats.pages_scored += 1
                self._emit_progress("score", i + 1, len(filtered_pages))

            # Stage 5: Tag
            logger.info("Stage 5/6: Tagging %d pages", len(filtered_pages))
            self._emit_progress("tag", 0, len(filtered_pages))
            for i, page in enumerate(filtered_pages):
                tags = self._auto_tag_page(page)
                stats.pages_tagged += 1
                stats.tags_applied += len(tags)
                if tags:
                    stats.interests_matched += 1
                self._emit_progress("tag", i + 1, len(filtered_pages))

            # Stage 6: Index
            logger.info("Stage 6/6: Indexing %d pages", len(filtered_pages))
            self._emit_progress("index", 0, len(filtered_pages))
            for i, page in enumerate(filtered_pages):
                self._search_index.add_page(page)
                stats.pages_indexed += 1
                self._emit_progress("index", i + 1, len(filtered_pages))

        except (RuntimeError, OSError) as e:
            logger.error("Pipeline error: %s", e)
            stats.errors.append(str(e))
        finally:
            stats.elapsed_seconds = time.time() - start_time

        return stats

    def _read_file_as_page(self, filepath: str) -> CrawledPage | None:
        """Read a local file and convert it to a CrawledPage."""
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            title = os.path.basename(filepath)
            # Try to extract title from markdown/html
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

    def _auto_tag_page(self, page: CrawledPage) -> list[str]:
        """Auto-tag a page based on interest matching."""
        text = f'{page.title} {page.content}'
        matches = self._interest_store.matches_any(text, page.url)
        tags = []
        for interest in matches:
            self._tag_store.add_tag_to_page(page.url, interest.name)
            tags.append(interest.name)
        # Add keyword-based tags
        from personal_index.keyword_extractor import extract_keywords
        keywords = extract_keywords(page.content, max_keywords=5)
        for kw in keywords:
            self._tag_store.add_tag_to_page(page.url, kw)
            tags.append(kw)
        return tags

    def add_page_directly(self, page: CrawledPage) -> bool:
        """Add a page directly through the pipeline (skip crawl)."""
        if not page.content:
            return False

        if not self._filter.should_include(page):
            return False

        keyword_matches = 0
        total_keywords = 0
        matched_interests = []
        for interest in self._interest_store.list_all():
            for kw in interest.keywords:
                total_keywords += 1
                if kw.lower() in page.content.lower():
                    keyword_matches += 1
                    matched_interests.append(interest.name)

        score_result = self._scorer.score(
            keyword_matches=keyword_matches,
            total_keywords=max(total_keywords, 1),
            word_count=len(page.content.split()),
            domain_authority=0.5,
        )
        score_val = score_result.total
        page.relevance_score = score_val

        if score_val < self.pipeline_config.min_score_threshold:
            return False

        tags = self._auto_tag_page(page)
        for tag_name in tags:
            self._tag_store.add_tag_to_page(page.url, tag_name)

        try:
            self._search_index.add_page(page)
            return True
        except (OSError, ValueError):
            return False

    def close(self) -> None:
        """Close all resources."""
        self._crawler.close()
        self._search_index.close()
        self._tag_store._save()
        self._interest_store._save()
