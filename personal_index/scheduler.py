"""Scheduled crawling module for periodic re-scanning of tracked topics."""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, List, Optional

from personal_index.config import AppConfig, ScheduleConfig

logger = logging.getLogger(__name__)


@dataclass
class ScheduleEntry:
    """Represents a scheduled crawl task."""

    name: str
    interval_hours: int = 24
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    enabled: bool = True
    seed_urls: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "interval_hours": self.interval_hours,
            "last_run": self.last_run,
            "next_run": self.next_run,
            "enabled": self.enabled,
            "seed_urls": self.seed_urls,
            "topics": self.topics,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScheduleEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class CrawlScheduler:
    """Manages scheduled crawling tasks."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig()
        self.entries: List[ScheduleEntry] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._crawl_callback: Optional[Callable] = None
        self._lock = threading.Lock()

    def set_crawl_callback(self, callback: Callable) -> None:
        """Set the callback function to execute when a crawl is triggered."""
        self._crawl_callback = callback

    def add_schedule(
        self,
        name: str,
        interval_hours: int = 24,
        seed_urls: List[str] = None,
        topics: List[str] = None,
    ) -> ScheduleEntry:
        """Add a new scheduled crawl task."""
        if seed_urls is None:
            seed_urls = []
        if topics is None:
            topics = []

        entry = ScheduleEntry(
            name=name,
            interval_hours=interval_hours,
            seed_urls=seed_urls,
            topics=topics,
        )
        self.entries.append(entry)
        logger.info(f"Added schedule: {name} every {interval_hours}h")
        return entry

    def remove_schedule(self, name: str) -> bool:
        """Remove a scheduled crawl task by name."""
        for i, entry in enumerate(self.entries):
            if entry.name == name:
                self.entries.pop(i)
                logger.info(f"Removed schedule: {name}")
                return True
        return False

    def enable_schedule(self, name: str) -> bool:
        """Enable a scheduled crawl task."""
        for entry in self.entries:
            if entry.name == name:
                entry.enabled = True
                return True
        return False

    def disable_schedule(self, name: str) -> bool:
        """Disable a scheduled crawl task."""
        for entry in self.entries:
            if entry.name == name:
                entry.enabled = False
                return True
        return False

    def get_schedule(self, name: str) -> Optional[ScheduleEntry]:
        """Get a schedule entry by name."""
        for entry in self.entries:
            if entry.name == name:
                return entry
        return None

    def list_schedules(self) -> List[ScheduleEntry]:
        """List all scheduled crawl tasks."""
        return list(self.entries)

    def run_due(self) -> List[str]:
        """Run all due scheduled tasks. Returns list of executed task names."""
        now = datetime.now(timezone.utc)
        executed = []

        for entry in self.entries:
            if not entry.enabled:
                continue

            should_run = False
            if entry.last_run is None:
                should_run = True
            else:
                last_run = datetime.fromisoformat(entry.last_run)
                elapsed = (now - last_run).total_seconds() / 3600
                if elapsed >= entry.interval_hours:
                    should_run = True

            if should_run and self._crawl_callback:
                logger.info(f"Running scheduled crawl: {entry.name}")
                try:
                    self._crawl_callback(entry)
                    entry.last_run = now.isoformat()
                    executed.append(entry.name)
                except Exception as e:
                    logger.error(f"Error running schedule {entry.name}: {e}")

        return executed

    def start(self, poll_interval: int = 60) -> None:
        """Start the scheduler in a background thread."""
        if self._running:
            return

        self._running = True

        def _run():
            while self._running:
                try:
                    self.run_due()
                except Exception as e:
                    logger.error(f"Scheduler error: {e}")
                time.sleep(poll_interval)

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        logger.info("Scheduler started")

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Scheduler stopped")

    def is_running(self) -> bool:
        """Check if the scheduler is running."""
        return self._running

    def get_stats(self) -> dict:
        """Get scheduler statistics."""
        return {
            "total_schedules": len(self.entries),
            "enabled": sum(1 for e in self.entries if e.enabled),
            "disabled": sum(1 for e in self.entries if not e.enabled),
            "running": self._running,
        }
