"""Pipeline runner that orchestrates the full crawl→extract→filter→score→tag→index pipeline."""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

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
            crawled_pages = []
            for i, url in enumerate(seed_urls):
                try:
                    pages = self._crawler.crawl(url, max_depth=max_depth)
                    crawled_pages.extend(pages)
                    stats.pages_crawled += len(pages)
                    self._emit_progress("crawl", i + 1, len(seed_urls))
                except Exception as e:
                    stats.errors.append(f"Crawl error for {url}: {e}")
                    logger.error("Crawl error for %s: %s", url, e)

            # Stage 2: Extract
            logger.info("Stage 2/6: Extracting content from %d pages", len(crawled_pages))
            self._emit_progress("extract", 0, len(crawled_pages))
            extracted_pages = []
            for i, page in enumerate(crawled_pages):
                try:
                    if page.content:
                        extracted_pages.append(page)
                        stats.pages_extracted += 1
                    self._emit_progress("extract", i + 1, len(crawled_pages))
                except Exception as e:
                    stats.errors.append(f"Extract error for {page.url}: {e}")

            # Stage 3: Filter
            logger.info("Stage 3/6: Filtering %d pages", len(extracted_pages))
            self._emit_progress("filter", 0, len(extracted_pages))
            filtered_pages = []
            for i, page in enumerate(extracted_pages):
                try:
                    if self._filter.should_include(page):
                        filtered_pages.append(page)
                        stats.pages_filtered_in += 1
                    else:
                        stats.pages_filtered_out += 1
                    self._emit_progress("filter", i + 1, len(extracted_pages))
                except Exception as e:
                    stats.errors.append(f"Filter error for {page.url}: {e}")

            # Stage 4: Score
            logger.info("Stage 4/6: Scoring %d pages", len(filtered_pages))
            self._emit_progress("score", 0, len(filtered_pages))
            scored_pages = []
            for i, page in enumerate(filtered_pages):
                try:
                    score_result = self._score_page(page)
                    page.relevance_score = score_result.total
                    scored_pages.append(page)
                    stats.pages_scored += 1
                    self._emit_progress("score", i + 1, len(filtered_pages))
                except Exception as e:
                    stats.errors.append(f"Score error for {page.url}: {e}")

            # Stage 5: Tag
            logger.info("Stage 5/6: Tagging %d pages", len(scored_pages))
            self._emit_progress("tag", 0, len(scored_pages))
            tagged_pages = []
            for i, page in enumerate(scored_pages):
                try:
                    tags, interests_matched = self._auto_tag_page(page)
                    stats.tags_applied += len(tags)
                    stats.interests_matched += interests_matched
                    tagged_pages.append(page)
                    stats.pages_tagged += 1
                    self._emit_progress("tag", i + 1, len(scored_pages))
                except Exception as e:
                    stats.errors.append(f"Tag error for {page.url}: {e}")

            # Stage 6: Index
            logger.info("Stage 6/6: Indexing %d pages", len(tagged_pages))
            self._emit_progress("index", 0, len(tagged_pages))
            for i, page in enumerate(tagged_pages):
                try:
                    # Enforce minimum score threshold before indexing
                    if page.relevance_score < self.pipeline_config.min_score_threshold:
                        stats.pages_filtered_out += 1
                        continue
                    self._search_index.add_page(page)
                    stats.pages_indexed += 1
                    self._emit_progress("index", i + 1, len(tagged_pages))
                except Exception as e:
                    stats.errors.append(f"Index error for {page.url}: {e}")

        finally:
            stats.elapsed_seconds = time.time() - start_time

        logger.info("Pipeline complete: %s", stats.summary())
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
            logger.info("Stage 1/6: Reading %d files", len(file_paths))
            self._emit_progress("crawl", 0, len(file_paths))
            crawled_pages = []
            for i, filepath in enumerate(file_paths):
                try:
                    page = self._read_file(filepath)
                    if page:
                        crawled_pages.append(page)
                        stats.pages_crawled += 1
                    else:
                        # File was empty or unreadable - record as error
                        if not os.path.isfile(filepath):
                            stats.errors.append(f"File not found: {filepath}")
                        else:
                            stats.errors.append(f"Empty or unreadable file: {filepath}")
                    self._emit_progress("crawl", i + 1, len(file_paths))
                except Exception as e:
                    stats.errors.append(f"Read error for {filepath}: {e}")

            # Stage 2: Extract
            logger.info("Stage 2/6: Extracting content from %d pages", len(crawled_pages))
            self._emit_progress("extract", 0, len(crawled_pages))
            extracted_pages = []
            for i, page in enumerate(crawled_pages):
                try:
                    if page.content:
                        extracted_pages.append(page)
                        stats.pages_extracted += 1
                    self._emit_progress("extract", i + 1, len(crawled_pages))
                except Exception as e:
                    stats.errors.append(f"Extract error for {page.url}: {e}")

            # Stage 3: Filter
            logger.info("Stage 3/6: Filtering %d pages", len(extracted_pages))
            self._emit_progress("filter", 0, len(extracted_pages))
            filtered_pages = []
            for i, page in enumerate(extracted_pages):
                try:
                    if self._filter.should_include(page):
                        filtered_pages.append(page)
                        stats.pages_filtered_in += 1
                    else:
                        stats.pages_filtered_out += 1
                    self._emit_progress("filter", i + 1, len(extracted_pages))
                except Exception as e:
                    stats.errors.append(f"Filter error for {page.url}: {e}")

            # Stage 4: Score
            logger.info("Stage 4/6: Scoring %d pages", len(filtered_pages))
            self._emit_progress("score", 0, len(filtered_pages))
            scored_pages = []
            for i, page in enumerate(filtered_pages):
                try:
                    score_result = self._score_page(page)
                    page.relevance_score = score_result.total
                    scored_pages.append(page)
                    stats.pages_scored += 1
                    self._emit_progress("score", i + 1, len(filtered_pages))
                except Exception as e:
                    stats.errors.append(f"Score error for {page.url}: {e}")

            # Stage 5: Tag
            logger.info("Stage 5/6: Tagging %d pages", len(scored_pages))
            self._emit_progress("tag", 0, len(scored_pages))
            tagged_pages = []
            for i, page in enumerate(scored_pages):
                try:
                    tags, interests_matched = self._auto_tag_page(page)
                    stats.tags_applied += len(tags)
                    stats.interests_matched += interests_matched
                    tagged_pages.append(page)
                    stats.pages_tagged += 1
                    self._emit_progress("tag", i + 1, len(scored_pages))
                except Exception as e:
                    stats.errors.append(f"Tag error for {page.url}: {e}")

            # Stage 6: Index
            logger.info("Stage 6/6: Indexing %d pages", len(tagged_pages))
            self._emit_progress("index", 0, len(tagged_pages))
            for i, page in enumerate(tagged_pages):
                try:
                    # Enforce minimum score threshold before indexing
                    if page.relevance_score < self.pipeline_config.min_score_threshold:
                        stats.pages_filtered_out += 1
                        continue
                    self._search_index.add_page(page)
                    stats.pages_indexed += 1
                    self._emit_progress("index", i + 1, len(tagged_pages))
                except Exception as e:
                    stats.errors.append(f"Index error for {page.url}: {e}")

        finally:
            stats.elapsed_seconds = time.time() - start_time

        logger.info("Pipeline complete: %s", stats.summary())
        return stats

    def _read_file(self, filepath: str) -> CrawledPage | None:
        """Read a file and create a CrawledPage from it.

        Handles plain text (.txt, .md, .rst) and HTML (.html, .htm) files.
        For HTML files, uses ContentExtractor to extract meaningful text.
        For plain text files, reads content directly.
        """
        if not os.path.isfile(filepath):
            return None

        ext = os.path.splitext(filepath)[1].lower()
        title = os.path.basename(filepath)

        if ext in ('.html', '.htm'):
            # HTML file: use ContentExtractor
            from personal_index.content_extractor import ContentExtractor
            extractor = ContentExtractor()
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                html_content = f.read()
            extracted = extractor.extract(html_content)
            content = extracted.text or ""
            if extracted.title:
                title = extracted.title
        else:
            # Plain text file: read directly
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

        if not content or not content.strip():
            return None

        content = content.strip()
        return CrawledPage(
            url=filepath,
            title=title,
            content=content,
            status_code=200,
            word_count=len(content.split()),
            crawled_at=datetime.now(timezone.utc),
        )

    def _score_page(self, page: CrawledPage) -> ScoreWeights:
        """Score a page based on interest matching."""
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
        return score_result

    def _auto_tag_page(self, page: CrawledPage) -> tuple[list[str], int]:
        """Auto-tag a page based on interest matching.

        Returns:
            Tuple of (tags list, number of interests matched)
        """
        text = f'{page.title} {page.content}'
        matches = self._interest_store.matches_any(text, page.url)
        tags = []
        interests_matched = 0
        for interest in matches:
            self._tag_store.add_tag_to_page(page.url, interest.name)
            tags.append(interest.name)
            interests_matched += 1
        # Add keyword-based tags
        from personal_index.keyword_extractor import extract_keywords
        keywords = extract_keywords(page.content, max_keywords=5)
        for kw in keywords:
            self._tag_store.add_tag_to_page(page.url, kw)
            tags.append(kw)
        return tags, interests_matched

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

        tags, _ = self._auto_tag_page(page)
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
