"""Application factory - wires all modules together."""

from __future__ import annotations

import logging
import os

from personal_index.config.loader import load_config
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
        self._config = None
        self._interest_store = None
        self._search_index = None
        self._content_search = None
        self._scheduler = None
        self._pipeline = None
        self._initialized = False

    @property
    def config(self):
        """Load and return application configuration."""
        if self._config is None:
            self._config = self._load_config()
        return self._config

    @property
    def interest_store(self):
        """Get the interest store singleton."""
        if self._interest_store is None:
            store_path = os.path.join(self.data_dir, "interests.json")
            self._interest_store = InterestStore(store_path=store_path)
        return self._interest_store

    @property
    def search_index(self):
        """Get the search index singleton."""
        if self._search_index is None:
            self._search_index = SearchIndex()
        return self._search_index

    @property
    def content_search(self):
        """Get the content search singleton."""
        if self._content_search is None:
            self._content_search = ContentSearch()
            # Use our existing search index
            self._content_search.index = self.search_index
        return self._content_search

    @property
    def scheduler(self):
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
    def pipeline(self):
        """Get the content processing pipeline."""
        if self._pipeline is None:
            self._pipeline = self._build_pipeline()
        return self._pipeline

    def _load_config(self):
        """Load configuration from file or use defaults."""
        try:
            return load_config(self.config_path)
        except (FileNotFoundError, OSError):
            logger.info("No config file found, using defaults")
            from personal_index.config.models import (
                AppConfig,
                CrawlConfig,
                IndexConfig,
                SchedulerConfig,
            )
            return AppConfig(
                data_dir=self.data_dir,
                crawl=CrawlConfig(),
                scheduler=SchedulerConfig(),
                index=IndexConfig(),
            )

    def _build_pipeline(self):
        """Build the default content processing pipeline."""
        from personal_index.content_extractor import ContentExtractor
        from personal_index.content_filter import ContentFilter, FilterConfig
        from personal_index.content_scoring import ContentScorer, ScoreWeights
        from personal_index.content_tagger import ContentTagger

        pipeline = ContentPipeline(name="default")

        # Step 1: Extract text content
        extractor = ContentExtractor()

        def extract_step(data: dict) -> dict:

            raw = data.get("raw_content", data.get("content", ""))
            extracted = extractor.extract(raw)
            data["extracted_text"] = extracted.text
            data["title"] = data.get("title") or extracted.title or "Untitled"
            return data

        pipeline.add_step("extract", extract_step, on_error="continue")

        # Step 2: Filter content
        filter_config = FilterConfig()
        content_filter = ContentFilter(config=filter_config)

        def filter_step(data: dict) -> dict:
            from personal_index.models import CrawledPage
            page = CrawledPage(
                url=data.get("url", ""),
                title=data.get("title", ""),
                content=data.get("extracted_text", data.get("text", "")),
            )
            data["passes_filter"] = content_filter.should_include(page)
            return data

        pipeline.add_step("filter", filter_step, on_error="continue")

        # Step 3: Score content
        scorer = ContentScorer(weights=ScoreWeights())

        def score_step(data: dict) -> dict:
            text = data.get("extracted_text", data.get("text", ""))

            word_count = len(text.split()) if text else 0
            # Count keyword matches (simplified)
            keywords = []
            for interest in self.interest_store.list_all():
                if interest.enabled:
                    keywords.extend(interest.keywords)
            keyword_matches = sum(1 for kw in keywords if kw.lower() in text.lower())
            
            from datetime import datetime, timezone
            score = scorer.score(
                published_at=None,
                updated_at=datetime.now(timezone.utc),
                keyword_matches=keyword_matches,
                total_keywords=len(keywords) if keywords else 1,
                view_count=0,
                bookmark_count=0,
                share_count=0,
                word_count=word_count,
            )
            data["score"] = score.total
            return data

        pipeline.add_step("score", score_step, on_error="continue")

        # Step 4: Tag content
        tagger = ContentTagger()

        def tag_step(data: dict) -> dict:
            text = data.get("extracted_text", data.get("text", ""))
            data["tags"] = tagger.tag(text, min_confidence=0.5).tags
            return data

        pipeline.add_step("tag", tag_step, on_error="continue")

        return pipeline

    def initialize(self):
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

    def shutdown(self):
        """Clean up application resources."""
        if self._interest_store:
            # InterestStore doesn't have a save method, just pass
            pass
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

        if result.get("passes_filter", True):
            # Add to search index
            item_id = result.get("url", "")
            self.search_index.add_item({
                "id": item_id,
                "url": result.get("url", ""),
                "title": result.get("title", "Untitled"),
                "content": result.get("extracted_text", ""),
                "score": result.get("score", 0),
                "tags": result.get("tags", []),
            })

        return result  # type: ignore[no-any-return]

    def search(self, query: str, limit: int = 20) -> list:
        """Search indexed content."""
        self.initialize()
        result = self.content_search.search(query, limit=limit)
        # ContentSearch.search returns {"results": [...], "total": N, "query": "..."}
        items = result.get("results", [])
        # Each item is {"item": {...}, "score": float}
        out = []
        for entry in items:
            if isinstance(entry, dict) and "item" in entry:
                item = entry["item"]
                item["score"] = entry.get("score", 0)
                out.append(item)
            elif isinstance(entry, dict):
                out.append(entry)
            elif hasattr(entry, "to_dict"):
                out.append(entry.to_dict())
            else:
                out.append(entry)
        return out

    def add_interest(self, name: str, keywords=None, url_patterns=None, priority: int = 5):
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
