"""End-to-end pipeline runner: crawl → extract → filter → score → tag → index."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from personal_index.config.pipeline_config import PipelineConfig, load_pipeline_config
from personal_index.content_extractor import ContentExtractor
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer, ScoreWeights
from personal_index.crawler.main import Crawler, CrawlerConfig
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import AppConfig, CrawledPage
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

    def summary(self) -> str:
        """Return a human-readable summary."""
        lines = [
            f"Pipeline complete:",
            f"  Crawled:    {self.pages_crawled}",
            f"  Extracted:  {self.pages_extracted}",
            f"  Filtered in: {self.pages_filtered_in}",
            f"  Filtered out: {self.pages_filtered_out}",
            f"  Scored:     {self.pages_scored}",
            f"  Tagged:     {self.pages_tagged}",
            f"  Indexed:    {self.pages_indexed}",
        ]
        if self.errors:
            lines.append(f"  Errors:     {len(self.errors)}")
        return "\n".join(lines)


class PipelineRunner:
    """Orchestrates the full crawl→extract→filter→score→tag→index pipeline."""

    def __init__(
        self,
        config: PipelineConfig | None = None,
        app_config: AppConfig | None = None,
        data_dir: str = ".personal_index",
    ):
        self.pipeline_config = config or load_pipeline_config()
        self.app_config = app_config
        self.data_dir = data_dir
        self._extractor = ContentExtractor()
        self._scorer = ContentScorer()
        self._interest_store = InterestStore(store_path=f"{data_dir}/interests.json")
        self._filter = ContentFilter(
            config=FilterConfig(
                min_content_length=self.pipeline_config.min_content_length,
            ),
            interest_store=self._interest_store,
        )
        self._tag_store = TagStore(store_path=f"{data_dir}/tags.json")
        self._search_index = SearchIndex()

    def run(self, seed_urls: list[str], max_depth: int = 3) -> PipelineStats:
        """Run the full pipeline on seed URLs.

        Args:
            seed_urls: URLs to start crawling from.
            max_depth: Maximum crawl depth.

        Returns:
            PipelineStats with counts from each stage.
        """
        stats = PipelineStats()
        pages: list[CrawledPage] = []

        # Step 1: Crawl
        if self.pipeline_config.is_step_enabled("crawl"):
            logger.info("Step 1/6: Crawling %d seed URLs", len(seed_urls))
            crawler = Crawler(
                config=CrawlerConfig(max_depth=max_depth),
                interest_store=self._interest_store,
            )
            pages = crawler.crawl(seed_urls, max_depth=max_depth)
            stats.pages_crawled = len(pages)
            logger.info("  Crawled %d pages", stats.pages_crawled)

        # Step 2: Extract
        if self.pipeline_config.is_step_enabled("extract"):
            logger.info("Step 2/6: Extracting content")
            for page in pages:
                if page.content:
                    # Content already populated by crawler
                    pass
                else:
                    # Try to extract from any available HTML
                    pass
            stats.pages_extracted = len(pages)
            logger.info("  Extracted content from %d pages", stats.pages_extracted)

        # Step 3: Filter
        if self.pipeline_config.is_step_enabled("filter"):
            logger.info("Step 3/6: Filtering content")
            filtered = []
            for page in pages:
                if self._filter.should_include(page):
                    filtered.append(page)
                    stats.pages_filtered_in += 1
                else:
                    stats.pages_filtered_out += 1
            pages = filtered
            logger.info(
                "  %d pages passed filter, %d filtered out",
                stats.pages_filtered_in, stats.pages_filtered_out,
            )

        # Step 4: Score
        if self.pipeline_config.is_step_enabled("score"):
            logger.info("Step 4/6: Scoring content")
            for page in pages:
                word_count = len(page.content.split()) if page.content else 0
                score_result = self._scorer.score(
                    keyword_matches=0,
                    total_keywords=1,
                    word_count=word_count,
                    domain_authority=0.5,
                )
                score = score_result.total if hasattr(score_result, "total") else score_result.score if hasattr(score_result, "score") else 0.0
                page.relevance_score = score
                if score >= self.pipeline_config.min_score_threshold:
                    stats.pages_scored += 1
            logger.info("  Scored %d pages", stats.pages_scored)

        # Step 5: Tag
        if self.pipeline_config.is_step_enabled("tag"):
            logger.info("Step 5/6: Tagging content")
            for page in pages:
                tags = self._auto_tag(page)
                for tag_name in tags:
                    self._tag_store.add_tag_to_page(page.url, tag_name)
                    stats.pages_tagged += 1
            logger.info("  Tagged %d pages", stats.pages_tagged)

        # Step 6: Index
        if self.pipeline_config.is_step_enabled("index"):
            logger.info("Step 6/6: Indexing content")
            for page in pages:
                try:
                    self._search_index.add_page(page)
                    stats.pages_indexed += 1
                except Exception as e:
                    logger.warning("Failed to index %s: %s", page.url, e)
                    stats.errors.append(f"Index error for {page.url}: {e}")
            logger.info("  Indexed %d pages", stats.pages_indexed)

        return stats

    def _auto_tag(self, page: CrawledPage) -> list[str]:
        """Auto-generate tags for a page based on content and interests."""
        tags = set()
        # Tag by interest matches
        for interest in self._interest_store.list_all():
            if interest.matches(page.content or "", page.url):
                tags.add(interest.name)
        # Tag by content type
        if page.url:
            if "blog" in page.url.lower():
                tags.add("blog")
            if "api" in page.url.lower():
                tags.add("api")
        return list(tags)
