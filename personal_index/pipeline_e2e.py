"""End-to-end pipeline module.

Provides a unified interface for running the complete
crawl → extract → filter → score → tag → index → search pipeline.

This module ties together all individual components into a
cohesive, testable pipeline that can be invoked from the CLI
or programmatically.
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
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest
from personal_index.tags import TagStore

logger = logging.getLogger(__name__)


@dataclass
class PipelineRunResult:
    """Complete result from an end-to-end pipeline run."""

    pages_crawled: int = 0
    pages_extracted: int = 0
    pages_filtered_in: int = 0
    pages_filtered_out: int = 0
    pages_scored: int = 0
    pages_tagged: int = 0
    pages_indexed: int = 0
    tags_applied: int = 0
    interests_matched: int = 0
    errors: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    indexed_pages: list[CrawledPage] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Whether the pipeline completed without critical errors."""
        return len(self.errors) == 0

    def summary(self) -> str:
        """Human-readable summary of the pipeline run."""
        lines = [
            "Pipeline Run Result",
            "=" * 50,
            f"  Pages crawled:    {self.pages_crawled}",
            f"  Pages extracted:  {self.pages_extracted}",
            f"  Filtered in:      {self.pages_filtered_in}",
            f"  Filtered out:     {self.pages_filtered_out}",
            f"  Pages scored:     {self.pages_scored}",
            f"  Pages tagged:     {self.pages_tagged}",
            f"  Tags applied:     {self.tags_applied}",
            f"  Pages indexed:    {self.pages_indexed}",
            f"  Interests matched:{self.interests_matched}",
            f"  Errors:           {len(self.errors)}",
            f"  Time:             {self.elapsed_seconds:.2f}s",
            "=" * 50,
        ]
        return "\n".join(lines)


class PipelineE2E:
    """End-to-end pipeline orchestrator.

    Wires together all components:
    crawl → extract → filter → score → tag → index → search

    Usage:
        pipeline = PipelineE2E(data_dir=".personal_index")
        result = pipeline.run_from_files(["article.txt"])
        results = pipeline.search("python")
    """

    def __init__(
        self,
        data_dir: str = ".personal_index",
        config: PipelineConfig | None = None,
    ):
        self.data_dir = data_dir
        self.config = config or PipelineConfig()

        # Ensure directories
        os.makedirs(data_dir, exist_ok=True)
        for subdir in ["cache", "archive", "backups"]:
            os.makedirs(os.path.join(data_dir, subdir), exist_ok=True)

        # Initialize stores
        self.interest_store = InterestStore(
            store_path=os.path.join(data_dir, "interests.json")
        )
        self.tag_store = TagStore(
            store_path=os.path.join(data_dir, "tags.json")
        )
        self.search_index = SearchIndex(
            db_path=os.path.join(data_dir, "search_index.json")
        )

        # Initialize processing components
        self.extractor = ContentExtractor()
        self.scorer = ContentScorer(weights=ScoreWeights())
        self.content_filter = ContentFilter(
            config=FilterConfig(
                min_content_length=self.config.min_content_length,
                require_interest_match=False,
            ),
            interest_store=self.interest_store,
        )

    def add_interest(self, name: str, keywords: list[str] | None = None,
                     priority: int = 5) -> None:
        """Add an interest to track."""
        interest = Interest(name=name, keywords=keywords or [], priority=priority)
        self.interest_store.add(interest)

    # ------------------------------------------------------------------
    # Stage methods (private)
    # ------------------------------------------------------------------

    def _stage_read(self, file_path: str) -> str | None:
        """Read a file and return its raw content, or None if not found."""
        if not os.path.exists(file_path):
            return None
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def _stage_extract(self, raw_content: str, file_path: str) -> CrawledPage:
        """Extract structured content from raw file content."""
        page = CrawledPage(
            url=f"file://{os.path.abspath(file_path)}",
            title=os.path.basename(file_path),
            content=raw_content,
            raw_html=raw_content if file_path.endswith((".html", ".htm")) else "",
        )
        if page.raw_html:
            extracted = self.extractor.extract(page.raw_html)
            if extracted.title:
                page.title = extracted.title
            if extracted.text:
                page.content = extracted.text
            page.word_count = extracted.word_count
        else:
            page.word_count = len(page.content.split())
        return page

    def _stage_filter(self, page: CrawledPage) -> bool:
        """Return True if the page passes the content filter."""
        return self.content_filter.should_include(page)

    def _stage_score(self, page: CrawledPage) -> float:
        """Score the page against interests and store matched interests."""
        keyword_matches = 0
        total_keywords = 0
        matched_interests: list[str] = []
        for interest in self.interest_store.list_all():
            for kw in interest.keywords:
                total_keywords += 1
                if kw.lower() in page.content.lower():
                    keyword_matches += 1
                    matched_interests.append(interest.name)

        page.matched_interests = matched_interests

        score_result = self.scorer.score(
            keyword_matches=keyword_matches,
            total_keywords=max(total_keywords, 1),
            word_count=page.word_count,
            domain_authority=0.5,
        )
        page.relevance_score = score_result.total
        return score_result.total

    def _stage_tag(self, page: CrawledPage) -> list[str]:
        """Tag the page with matched interests and extracted keywords."""
        tags = list(page.matched_interests)
        from personal_index.keyword_extractor import extract_keywords
        keywords = extract_keywords(page.content, max_keywords=5)
        tags.extend(keywords)
        for tag_name in tags:
            self.tag_store.add_tag_to_page(page.url, tag_name)
        return tags

    def _stage_index(self, page: CrawledPage) -> None:
        """Add the page to the search index."""
        self.search_index.add_page(page)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_from_files(self, file_paths: list[str]) -> PipelineRunResult:
        """Run the full pipeline on local files.

        Args:
            file_paths: List of file paths to process.

        Returns:
            PipelineRunResult with statistics.
        """
        result = PipelineRunResult()
        start_time = time.time()

        for file_path in file_paths:
            try:
                raw_content = self._stage_read(file_path)
                if raw_content is None:
                    result.errors.append(f"File not found: {file_path}")
                    continue

                result.pages_crawled += 1

                page = self._stage_extract(raw_content, file_path)
                result.pages_extracted += 1

                if not self._stage_filter(page):
                    result.pages_filtered_out += 1
                    continue
                result.pages_filtered_in += 1

                score = self._stage_score(page)
                result.pages_scored += 1

                if score < self.config.min_score_threshold:
                    continue

                tags = self._stage_tag(page)
                if tags:
                    result.pages_tagged += 1
                    result.tags_applied += len(tags)
                result.interests_matched += len(page.matched_interests)

                try:
                    self._stage_index(page)
                    result.pages_indexed += 1
                    result.indexed_pages.append(page)
                except (OSError, ValueError) as e:
                    result.errors.append(f"Index error for {page.url}: {e}")

            except (RuntimeError, OSError) as e:
                result.errors.append(f"Error processing {file_path}: {e}")

        result.elapsed_seconds = time.time() - start_time
        return result

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search the indexed content.

        Args:
            query: Search query string.
            limit: Maximum number of results.

        Returns:
            List of search result dictionaries.
        """
        results = self.search_index.search(query, limit=limit)
        return [
            {
                "url": r.url,
                "title": r.title,
                "score": r.relevance_score,
                "snippet": r.snippet,
                "tags": self.tag_store.get_tags_for_page(r.url),
            }
            for r in results
        ]

    def close(self) -> None:
        """Close all resources and persist state."""
        self.search_index.close()
        self.tag_store._save()
        self.interest_store._save()
