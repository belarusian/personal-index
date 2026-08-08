"""Scheduled crawling module for periodic re-scanning of tracked topics."""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.crawler import Crawler, CrawlerConfig
from personal_index.interest_store import InterestStore
from personal_index.models import CrawledPage
from personal_index.search_index import SearchIndex

logger = logging.getLogger(__name__)


@dataclass
class ScheduleConfig:
    """Configuration for scheduled crawling."""

    interval_hours: int = 24
    enabled: bool = True
    seed_urls: list[str] = field(default_factory=list)
    max_pages_per_run: int = 50
    crawl_depth: int = 2
    delay: float = 1.0


@dataclass
class ScheduleEntry:
    """A single scheduled crawl entry."""

    name: str
    config: ScheduleConfig
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    total_pages_indexed: int = 0


class ScheduleStore:
    """Persistent store for schedule entries."""

    def __init__(self, path: str = "~/.personal-index/schedules.json"):
        self._path = Path(path).expanduser()
        self._entries: dict[str, ScheduleEntry] = {}
        self._load()

    def _load(self) -> None:
        """Load schedules from disk."""
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text())
                for name, entry_data in data.items():
                    config = ScheduleConfig(
                        interval_hours=entry_data.get("interval_hours", 24),
                        enabled=entry_data.get("enabled", True),
                        seed_urls=entry_data.get("seed_urls", []),
                        max_pages_per_run=entry_data.get("max_pages_per_run", 50),
                        crawl_depth=entry_data.get("crawl_depth", 2),
                        delay=entry_data.get("delay", 1.0),
                    )
                    last_run = None
                    if entry_data.get("last_run"):
                        last_run = datetime.fromisoformat(entry_data["last_run"])
                    next_run = None
                    if entry_data.get("next_run"):
                        next_run = datetime.fromisoformat(entry_data["next_run"])
                    self._entries[name] = ScheduleEntry(
                        name=name,
                        config=config,
                        last_run=last_run,
                        next_run=next_run,
                        run_count=entry_data.get("run_count", 0),
                        total_pages_indexed=entry_data.get("total_pages_indexed", 0),
                    )
            except (json.JSONDecodeError, KeyError):
                self._entries.clear()
        else:
            self._path.parent.mkdir(parents=True, exist_ok=True)

    def _save(self) -> None:
        """Save schedules to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        for name, entry in self._entries.items():
            data[name] = {
                "interval_hours": entry.config.interval_hours,
                "enabled": entry.config.enabled,
                "seed_urls": entry.config.seed_urls,
                "max_pages_per_run": entry.config.max_pages_per_run,
                "crawl_depth": entry.config.crawl_depth,
                "delay": entry.config.delay,
                "last_run": entry.last_run.isoformat() if entry.last_run else None,
                "next_run": entry.next_run.isoformat() if entry.next_run else None,
                "run_count": entry.run_count,
                "total_pages_indexed": entry.total_pages_indexed,
            }
        self._path.write_text(json.dumps(data, indent=2))

    def add(self, entry: ScheduleEntry) -> None:
        """Add a schedule entry."""
        self._entries[entry.name] = entry
        self._save()

    def remove(self, name: str) -> bool:
        """Remove a schedule entry."""
        if name in self._entries:
            del self._entries[name]
            self._save()
            return True
        return False

    def get(self, name: str) -> Optional[ScheduleEntry]:
        """Get a schedule entry by name."""
        return self._entries.get(name)

    def list_all(self) -> list[ScheduleEntry]:
        """List all schedule entries."""
        return list(self._entries.values())

    def update(self, entry: ScheduleEntry) -> None:
        """Update a schedule entry."""
        self._entries[entry.name] = entry
        self._save()


class Scheduler:
    """Manages scheduled crawling jobs."""

    def __init__(
        self,
        interest_store: Optional[InterestStore] = None,
        search_index: Optional[SearchIndex] = None,
        schedule_store: Optional[ScheduleStore] = None,
    ):
        self.interest_store = interest_store
        self.search_index = search_index
        self.schedule_store = schedule_store or ScheduleStore()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def add_schedule(
        self,
        name: str,
        seed_urls: list[str],
        interval_hours: int = 24,
        max_pages: int = 50,
        depth: int = 2,
        delay: float = 1.0,
    ) -> ScheduleEntry:
        """Add a new scheduled crawl."""
        config = ScheduleConfig(
            interval_hours=interval_hours,
            enabled=True,
            seed_urls=seed_urls,
            max_pages_per_run=max_pages,
            crawl_depth=depth,
            delay=delay,
        )
        entry = ScheduleEntry(name=name, config=config)
        self.schedule_store.add(entry)
        return entry

    def remove_schedule(self, name: str) -> bool:
        """Remove a scheduled crawl."""
        return self.schedule_store.remove(name)

    def toggle_schedule(self, name: str) -> Optional[ScheduleEntry]:
        """Toggle a schedule on/off."""
        entry = self.schedule_store.get(name)
        if entry:
            entry.config.enabled = not entry.config.enabled
            self.schedule_store.update(entry)
        return entry

    def run_schedule(self, name: str) -> int:
        """Manually run a scheduled crawl. Returns pages indexed."""
        entry = self.schedule_store.get(name)
        if not entry or not entry.config.enabled:
            logger.warning(f"Schedule '{name}' not found or disabled")
            return 0

        config = entry.config
        crawler_config = CrawlerConfig(
            max_depth=config.crawl_depth,
            max_pages=config.max_pages_per_run,
            delay=config.delay,
        )

        crawler = Crawler(config=crawler_config, interest_store=self.interest_store)
        pages = crawler.crawl(config.seed_urls)

        if self.interest_store:
            filter_config = FilterConfig(
                require_interest_match=True,
            )
            content_filter = ContentFilter(
                config=filter_config,
                interest_store=self.interest_store,
            )
            pages = content_filter.filter_pages(pages)

        if self.search_index:
            for page in pages:
                self.search_index.add(page)

        entry.last_run = datetime.utcnow()
        entry.run_count += 1
        entry.total_pages_indexed += len(pages)
        self.schedule_store.update(entry)

        logger.info(
            f"Schedule '{name}' completed: {len(pages)} pages indexed"
        )
        return len(pages)

    def get_due_schedules(self) -> list[ScheduleEntry]:
        """Get schedules that are due to run."""
        now = datetime.utcnow()
        due = []
        for entry in self.schedule_store.list_all():
            if not entry.config.enabled:
                continue
            if entry.next_run is None or now >= entry.next_run:
                due.append(entry)
        return due

    def update_next_run_times(self) -> None:
        """Update next_run times for all schedules."""
        for entry in self.schedule_store.list_all():
            if entry.config.enabled:
                from datetime import timedelta
                if entry.last_run:
                    entry.next_run = entry.last_run + timedelta(
                        hours=entry.config.interval_hours
                    )
                else:
                    entry.next_run = datetime.utcnow()
                self.schedule_store.update(entry)
