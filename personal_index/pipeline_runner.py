"""Pipeline runner that orchestrates the full crawl→extract→filter→score→tag→index pipeline."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field

from personal_index.config.pipeline_config import PipelineConfig
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer
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

    def summary(self) -> str:
        """Return a human-readable summary of pipeline stats."""
        lines = [
            "Pipeline Summary",
            "-" * 40,
            f"Crawled:    {self.pages_crawled}",
            f"Extracted:  {self.pages_extracted}",
            f"Filtered in:  {self.pages_filtered_in}",
            f"Filtered out: {self.pages_filtered_out}",
            f"Scored:     {self.pages_scored}",
            f"Tagged:     {self.pages_tagged}",
            f"Indexed:    {self.pages_indexed}",
            f"Errors:     {len(self.errors)}",
            f"Time:       {self.elapsed_seconds:.2f}s",
        ]
        return "\n".join(lines)


class PipelineRunner:
    """Orchestrates the full content processing pipeline."""

    def __init__(
        self,
        config: PipelineConfig | None = None,
        data_dir: str = ".personal_index",
    ):
        self.pipeline_config = config or PipelineConfig()
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

        # Initialize sub-components
        self._interest_store = InterestStore(
            store_path=os.path.join(data_dir, "interests.json")
        )
        self._search_index = SearchIndex(
            db_path=os.path.join(data_dir, "search_index.json")
        )
        self._tag_store = TagStore(
            store_path=os.path.join(data_dir, "tags.json")
        )
        self._scorer = ContentScorer()
        self._filter = ContentFilter(
            config=FilterConfig(
                min_content_length=self.pipeline_config.min_content_length,
                require_interest_match=True,
            ),
            interest_store=self._interest_store,
        )

    def run(self, seed_urls: list[str], max_depth: int = 3) -> PipelineStats:
        """Run the full pipeline on seed URLs.

        Args:
            seed_urls: URLs to start crawling from. If empty, skips crawl step.
            max_depth: Maximum crawl depth.

        Returns:
            PipelineStats with results from each step.
        """
        start_time = time.time()
        stats = PipelineStats()
        pages: list[CrawledPage] = []

        # Step 1: Crawl
        if self.pipeline_config.is_step_enabled("crawl"):
            logger.info("Step 1/6: Crawling %d seed URLs", len(seed_urls))
            if not seed_urls:
                logger.info("  No seed URLs provided, skipping crawl")
            else:
                crawler = Crawler(
                    config=CrawlerConfig(max_depth=max_depth),
                    interest_store=self._interest_store,
                )
                try:
                    pages = crawler.crawl(seed_urls, max_depth=max_depth)
                    crawler.close()
                except (OSError, ValueError) as e:
                    logger.error("Crawl failed: %s", e)
                    stats.errors.append(f"Crawl error: {e}")
                stats.pages_crawled = len(pages)
                logger.info("  Crawled %d pages", stats.pages_crawled)

        # Step 2: Extract
        if self.pipeline_config.is_step_enabled("extract"):
            logger.info("Step 2/6: Extracting content from %d pages", len(pages))
            extracted_count = 0
            for page in pages:
                if page.content and len(page.content) > 0:
                    extracted_count += 1
                else:
                    page.content = ""
            stats.pages_extracted = extracted_count
            logger.info("  Extracted content from %d pages", stats.pages_extracted)

        # Step 3: Filter
        if self.pipeline_config.is_step_enabled("filter"):
            logger.info("Step 3/6: Filtering %d pages", len(pages))
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
            logger.info("Step 4/6: Scoring %d pages", len(pages))
            scored_pages = []
            for page in pages:
                word_count = len(page.content.split()) if page.content else 0
                keyword_matches = 0
                total_keywords = 0
                for interest in self._interest_store.list_all():
                    for kw in interest.keywords:
                        total_keywords += 1
                        if kw.lower() in (page.content or "").lower():
                            keyword_matches += 1
                score_result = self._scorer.score(
                    keyword_matches=keyword_matches,
                    total_keywords=max(total_keywords, 1),
                    word_count=word_count,
                    domain_authority=0.5,
                )
                score = score_result.total if hasattr(score_result, "total") else 0.0
                page.relevance_score = score
                if score >= self.pipeline_config.min_score_threshold:
                    scored_pages.append(page)
                    stats.pages_scored += 1
                else:
                    stats.pages_filtered_out += 1
            pages = scored_pages
            logger.info("  Scored %d pages above threshold", stats.pages_scored)

        # Step 5: Tag
        if self.pipeline_config.is_step_enabled("tag"):
            logger.info("Step 5/6: Tagging %d pages", len(pages))
            tagged_count = 0
            for page in pages:
                tags = self._auto_tag(page)
                for tag_name in tags:
                    self._tag_store.add_tag_to_page(page.url, tag_name)
                    tagged_count += 1
            stats.pages_tagged = tagged_count
            logger.info("  Applied %d tags", stats.pages_tagged)

        # Step 6: Index
        if self.pipeline_config.is_step_enabled("index"):
            logger.info("Step 6/6: Indexing %d pages", len(pages))
            for page in pages:
                try:
                    self._search_index.add_page(page)
                    stats.pages_indexed += 1
                except (OSError, ValueError) as e:
                    logger.warning("Failed to index %s: %s", page.url, e)
                    stats.errors.append(f"Index error for {page.url}: {e}")
            logger.info("  Indexed %d pages", stats.pages_indexed)

        stats.elapsed_seconds = time.time() - start_time
        return stats

    def _auto_tag(self, page: CrawledPage) -> list[str]:
        """Auto-generate tags for a page based on content and interests."""
        tags = set()
        # Tag by interest matches
        for interest in self._interest_store.list_all():
            if interest.matches(page.content or "", page.url):
                tags.add(interest.name)
        # Tag by content type heuristics
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
        # Tag by matched interests
        if page.matched_interests:
            for mi in page.matched_interests:
                tags.add(mi)
        return list(tags)

    def add_page_directly(self, page: CrawledPage) -> bool:
        """Add a page directly through the pipeline (skip crawl).

        Useful for importing content from non-web sources.
        """
        # Extract (already done for direct pages)
        if not page.content:
            return False

        # Filter
        if not self._filter.should_include(page):
            return False

        # Score
        word_count = len(page.content.split()) if page.content else 0
        keyword_matches = 0
        total_keywords = 0
        for interest in self._interest_store.list_all():
            for kw in interest.keywords:
                total_keywords += 1
                if kw.lower() in (page.content or "").lower():
                    keyword_matches += 1
        score_result = self._scorer.score(
            keyword_matches=keyword_matches,
            total_keywords=max(total_keywords, 1),
            word_count=word_count,
            domain_authority=0.5,
        )
        score = score_result.total if hasattr(score_result, "total") else 0.0
        page.relevance_score = score

        if score < self.pipeline_config.min_score_threshold:
            return False

        # Tag
        tags = self._auto_tag(page)
        for tag_name in tags:
            self._tag_store.add_tag_to_page(page.url, tag_name)

        # Index
        try:
            self._search_index.add_page(page)
            return True
        except (OSError, ValueError):
            return False
