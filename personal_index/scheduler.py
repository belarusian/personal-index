"""Scheduled crawling management."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from personal_index.interest_store import InterestStore
from personal_index.search_index import SearchIndex


@dataclass
class ScheduleConfig:
    """Configuration for a scheduled crawl job."""

    interval_hours: int = 24
    enabled: bool = True
    seed_urls: List[str] = field(default_factory=list)
    max_pages_per_run: int = 50
    crawl_depth: int = 2
    delay: float = 1.0


@dataclass
class ScheduleEntry:
    """A scheduled crawl entry."""

    name: str
    config: ScheduleConfig
    run_count: int = 0
    total_pages_indexed: int = 0
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


@dataclass
class ScheduleStore:
    """Persistent storage for schedule entries."""

    path: str
    _entries: Dict[str, ScheduleEntry] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        self._load()

    def _load(self) -> None:
        """Load entries from file."""
        if not os.path.exists(self.path):
            self._entries = {}
            return
        try:
            with open(self.path, "r") as f:
                data = json.load(f)
            self._entries = {}
            for name, entry_data in data.items():
                config = ScheduleConfig(**entry_data["config"])
                entry = ScheduleEntry(
                    name=name,
                    config=config,
                    run_count=entry_data.get("run_count", 0),
                    total_pages_indexed=entry_data.get("total_pages_indexed", 0),
                    last_run=datetime.fromisoformat(entry_data["last_run"])
                    if entry_data.get("last_run")
                    else None,
                    next_run=datetime.fromisoformat(entry_data["next_run"])
                    if entry_data.get("next_run")
                    else None,
                )
                self._entries[name] = entry
        except (json.JSONDecodeError, KeyError, TypeError):
            self._entries = {}

    def _save(self) -> None:
        """Save entries to file."""
        parent = Path(self.path).parent
        parent.mkdir(parents=True, exist_ok=True)
        data = {}
        for name, entry in self._entries.items():
            data[name] = {
                "config": asdict(entry.config),
                "run_count": entry.run_count,
                "total_pages_indexed": entry.total_pages_indexed,
                "last_run": entry.last_run.isoformat() if entry.last_run else None,
                "next_run": entry.next_run.isoformat() if entry.next_run else None,
            }
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)

    def add(self, entry: ScheduleEntry) -> None:
        """Add a schedule entry."""
        self._entries[entry.name] = entry
        self._save()

    def get(self, name: str) -> Optional[ScheduleEntry]:
        """Get a schedule entry by name."""
        return self._entries.get(name)

    def remove(self, name: str) -> bool:
        """Remove a schedule entry by name."""
        if name in self._entries:
            del self._entries[name]
            self._save()
            return True
        return False

    def update(self, entry: ScheduleEntry) -> None:
        """Update a schedule entry."""
        self._entries[entry.name] = entry
        self._save()

    def list_all(self) -> List[ScheduleEntry]:
        """List all schedule entries."""
        return list(self._entries.values())


@dataclass
class Scheduler:
    """Manages scheduled crawling jobs."""

    interest_store: InterestStore
    search_index: SearchIndex
    schedule_store: ScheduleStore

    def add_schedule(
        self,
        name: str,
        seed_urls: List[str],
        interval_hours: int = 24,
        max_pages_per_run: int = 50,
        crawl_depth: int = 2,
        delay: float = 1.0,
    ) -> ScheduleEntry:
        """Add a new scheduled crawl job."""
        config = ScheduleConfig(
            interval_hours=interval_hours,
            seed_urls=seed_urls,
            max_pages_per_run=max_pages_per_run,
            crawl_depth=crawl_depth,
            delay=delay,
        )
        entry = ScheduleEntry(name=name, config=config)
        entry.next_run = datetime.utcnow()
        self.schedule_store.add(entry)
        return entry

    def remove_schedule(self, name: str) -> bool:
        """Remove a scheduled crawl job."""
        return self.schedule_store.remove(name)

    def toggle_schedule(self, name: str) -> Optional[ScheduleEntry]:
        """Toggle a schedule's enabled status."""
        entry = self.schedule_store.get(name)
        if entry is None:
            return None
        entry.config.enabled = not entry.config.enabled
        self.schedule_store.update(entry)
        return entry

    def get_due_schedules(self) -> List[ScheduleEntry]:
        """Get all schedules that are due to run."""
        now = datetime.utcnow()
        due = []
        for entry in self.schedule_store.list_all():
            if not entry.config.enabled:
                continue
            if entry.next_run is None or entry.next_run <= now:
                due.append(entry)
        return due

    def update_next_run_times(self) -> None:
        """Update next_run times for all schedules based on last_run."""
        for entry in self.schedule_store.list_all():
            if entry.last_run is not None:
                entry.next_run = entry.last_run + timedelta(hours=entry.config.interval_hours)
                self.schedule_store.update(entry)

    def run_schedule(self, name: str) -> int:
        """Run a scheduled crawl job. Returns number of pages indexed."""
        entry = self.schedule_store.get(name)
        if entry is None or not entry.config.enabled:
            return 0

        from personal_index.crawler import Crawler, CrawlerConfig

        config = CrawlerConfig(
            max_depth=entry.config.crawl_depth,
            max_pages=entry.config.max_pages_per_run,
            delay=entry.config.delay,
        )
        crawler = Crawler(config=config, interest_store=self.interest_store)
        pages = crawler.crawl(entry.config.seed_urls)
        crawler.close()

        for page in pages:
            self.search_index.add(page)

        entry.run_count += 1
        entry.total_pages_indexed += len(pages)
        entry.last_run = datetime.utcnow()
        entry.next_run = entry.last_run + timedelta(hours=entry.config.interval_hours)
        self.schedule_store.update(entry)

        return len(pages)

    def list_jobs(self) -> List[ScheduleEntry]:
        """List all scheduled jobs."""
        return self.schedule_store.list_all()


@dataclass
class ScheduledJob:
    """A scheduled crawl job (CLI-facing)."""

    name: str
    seed_urls: List[str] = field(default_factory=list)
    interval_hours: int = 24
    run_count: int = 0
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    enabled: bool = True
