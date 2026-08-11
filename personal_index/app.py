"""Application factory - wires all modules together."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from personal_index.config.loader import load_config
from personal_index.config.models import AppConfig, CrawlConfig, IndexConfig, SchedulerConfig
from personal_index.content_search import ContentSearch, SearchIndex
from personal_index.interests import InterestStore
from personal_index.pipeline import ContentPipeline
from personal_index.scheduler import Scheduler, ScheduleStore

logger = logging.getLogger(__name__)


class PersonalIndexApp:
    """Main application class that wires all modules together."""

    def __init__(self, config_path: str = "config.yaml", data_dir: str = ".personal_index"):
        self.config_path = config_path
        self.data_dir = data_dir
        self._config: AppConfig | None = None
        self._interest_store: InterestStore | None = None
        self._search_index: SearchIndex | None = None
        self._content_search: ContentSearch | None = None
        self._scheduler: Scheduler | None = None
        self._pipeline: ContentPipeline | None = None
        self._initialized = False

    @property
    def config(self) -> AppConfig:
        """Load and return application configuration."""
        if self._config is None:
            self._config = self._load_config()
        return self._config

    @property
    def interest_store(self) -> InterestStore:
        """Get the interest store singleton."""
        if self._interest_store is None:
            store_path = os.path.join(self.data_dir, "interests.json")
            self._interest_store = InterestStore(store_path=store_path)
        return self._interest_store

    @property
    def search_index(self) -> SearchIndex:
        """Get the search index singleton."""
        if self._search_index is None:
            self._search_index = SearchIndex()
        return self._search_index

    @property
    def content_search(self) -> ContentSearch:
        """Get the content search singleton."""
        if self._content_search is None:
            self._content_search = ContentSearch(self.search_index)
        return self._content_search

    @property
    def scheduler(self) -> Scheduler:
        """Get the scheduler singleton."""
        if self._scheduler is None:
            schedule_store = ScheduleStore(path=os.path.join(self.data_dir, "schedules.json"))
            self._scheduler = Scheduler(
                interest_store=self.interest_store,
                search_index=self.search_index,
                schedule_store=schedule_store,
            )
        return self._scheduler

    @property
    def pipeline(self) -> ContentPipeline:
        """Get the content processing pipeline."""
        if self._pipeline is None:
            self._pipeline = self._build_pipeline()
        return self._pipeline

    def _load_config(self) -> AppConfig:
        """Load configuration from file or use defaults."""
        try:
            return load_config(self.config_path)
        except (FileNotFoundError, OSError):
            logger.info("No config file found, using defaults")
            return AppConfig(
                data_dir=self.data_dir,
                crawl=CrawlConfig(),
                scheduler=SchedulerConfig(),
                index=IndexConfig(),
            )

    def _build_pipeline(self) -> ContentPipeline:
        """Build the default content processing pipeline."""
        from personal_index.content_extractor import extract_text
        from personal_index.content_filter import ContentFilter
        from personal_index.content_scoring import ContentScorer
        from personal_index.content_tagger import ContentTagger

        pipeline = ContentPipeline(name="default")

        # Step 1: Extract text content
        def extract_step(data: dict) -> dict:
            url = data.get("url", "")
            raw = data.get("raw_content", "")
            data["extracted_text"] = extract_text(raw) if raw else ""
            return data

        pipeline.add_step("extract", extract_step, on_error="continue")

        # Step 2: Filter content
        content_filter = ContentFilter()

        def filter_step(data: dict) -> dict:
            text = data.get("extracted_text", data.get("text", ""))
            data["passes_filter"] = content_filter.should_index(text)
            return data

        pipeline.add_step("filter", filter_step, on_error="continue")

        # Step 3: Score content
        scorer = ContentScorer()

        def score_step(data: dict) -> dict:
            text = data.get("extracted_text", data.get("text", ""))
            title = data.get("title", "")
            data["score"] = scorer.score(text, title)
            return data

        pipeline.add_step("score", score_step, on_error="continue")

        # Step 4: Tag content
        tagger = ContentTagger()

        def tag_step(data: dict) -> dict:
            text = data.get("extracted_text", data.get("text", ""))
            title = data.get("title", "")
            data["tags"] = tagger.tag(text, title)
            return data

        pipeline.add_step("tag", tag_step, on_error="continue")

        return pipeline

    def initialize(self) -> None:
        """Initialize all application components."""
        if self._initialized:
            return

        os.makedirs(self.data_dir, exist_ok=True)

        # Force initialization of all components
        _ = self.config
        _ = self.interest_store
        _ = self.search_index
        _ = self.content_search
        _ = self.pipeline

        self._initialized = True
        logger.info("PersonalIndexApp initialized with data_dir=%s", self.data_dir)

    def shutdown(self) -> None:
        """Clean up application resources."""
        if self._interest_store:
            self._interest_store.save()
        logger.info("PersonalIndexApp shutdown complete")

    def process_content(self, url: str, raw_content: str, title: str = "") -> dict:
        """Process content through the full pipeline."""
        self.initialize()

        data = {
            "url": url,
            "title": title,
            "raw_content": raw_content,
        }

        result = self.pipeline.run(data)

        if result.success and result.data.get("passes_filter", True):
            self.search_index.add_item(result.data)

        return result.data

    def search(self, query: str, limit: int = 20) -> list[dict]:
        """Search indexed content."""
        self.initialize()
        return self.content_search.search(query, limit=limit)

    def add_interest(self, name: str, keywords: list[str] | None = None,
                     url_patterns: list[str] | None = None, priority: int = 5) -> None:
        """Add a tracked interest."""
        from personal_index.models import Interest

        self.initialize()
        interest = Interest(
            name=name,
            keywords=keywords or [],
            url_patterns=url_patterns or [],
            priority=priority,
        )
        self.interest_store.add(interest)

    def get_stats(self) -> dict:
        """Get application statistics."""
        self.initialize()
        return {
            "indexed_items": len(self.search_index._items),
            "interests": len(self.interest_store.list_all()),
            "scheduled_jobs": len(self.scheduler.list_jobs()),
            "pipeline_steps": self.pipeline.step_count,
            "enabled_steps": self.pipeline.enabled_steps,
            "data_dir": self.data_dir,
        }
