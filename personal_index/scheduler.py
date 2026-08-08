"""Scheduled crawling module for periodic re-scanning of tracked topics."""

import time
import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set
from enum import Enum


class ScheduleState(Enum):
    """State of a scheduled crawl."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CrawlSchedule:
    """A scheduled crawl job."""
    name: str
    url: str
    interval_seconds: float = 3600  # default 1 hour
    max_depth: int = 3
    politeness_delay: float = 1.0
    enabled: bool = True
    state: ScheduleState = ScheduleState.PENDING
    last_run: Optional[float] = None
    next_run: Optional[float] = None
    run_count: int = 0
    error: Optional[str] = None

    def is_due(self) -> bool:
        """Check if this schedule is due to run."""
        if not self.enabled:
            return False
        if self.state == ScheduleState.RUNNING:
            return False
        if self.next_run is None:
            return True
        return time.time() >= self.next_run

    def mark_running(self) -> None:
        """Mark the schedule as running."""
        self.state = ScheduleState.RUNNING
        self.last_run = time.time()

    def mark_completed(self) -> None:
        """Mark the schedule as completed."""
        self.state = ScheduleState.COMPLETED
        self.run_count += 1
        self.next_run = time.time() + self.interval_seconds
        self.error = None

    def mark_failed(self, error: str) -> None:
        """Mark the schedule as failed."""
        self.state = ScheduleState.FAILED
        self.error = error
        self.next_run = time.time() + self.interval_seconds

    def schedule_next(self) -> None:
        """Schedule the next run."""
        self.next_run = time.time() + self.interval_seconds
        self.state = ScheduleState.PENDING


class CrawlScheduler:
    """Manages scheduled crawl jobs."""

    def __init__(self):
        self.schedules: Dict[str, CrawlSchedule] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._crawl_callback: Optional[Callable] = None
        self._check_interval: float = 60.0  # how often to check for due jobs

    def set_crawl_callback(self, callback: Callable) -> None:
        """Set the callback function to execute when a crawl is due."""
        self._crawl_callback = callback

    def add_schedule(self, schedule: CrawlSchedule) -> None:
        """Add a crawl schedule."""
        with self._lock:
            if schedule.name in self.schedules:
                raise ValueError(f"Schedule '{schedule.name}' already exists")
            schedule.schedule_next()
            self.schedules[schedule.name] = schedule

    def remove_schedule(self, name: str) -> None:
        """Remove a crawl schedule."""
        with self._lock:
            self.schedules.pop(name, None)

    def get_schedule(self, name: str) -> Optional[CrawlSchedule]:
        """Get a schedule by name."""
        return self.schedules.get(name)

    def list_schedules(self) -> List[CrawlSchedule]:
        """List all schedules."""
        return list(self.schedules.values())

    def get_due_schedules(self) -> List[CrawlSchedule]:
        """Get all schedules that are due to run."""
        return [s for s in self.schedules.values() if s.is_due()]

    def enable_schedule(self, name: str) -> None:
        """Enable a schedule."""
        schedule = self.schedules.get(name)
        if schedule:
            schedule.enabled = True
            if schedule.state == ScheduleState.CANCELLED:
                schedule.schedule_next()

    def disable_schedule(self, name: str) -> None:
        """Disable a schedule."""
        schedule = self.schedules.get(name)
        if schedule:
            schedule.enabled = False

    def run_due(self) -> int:
        """Run all due schedules. Returns number of jobs executed."""
        due = self.get_due_schedules()
        executed = 0
        for schedule in due:
            if self._crawl_callback:
                try:
                    schedule.mark_running()
                    self._crawl_callback(schedule)
                    schedule.mark_completed()
                    executed += 1
                except Exception as e:
                    schedule.mark_failed(str(e))
        return executed

    def start(self) -> None:
        """Start the scheduler loop."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the scheduler loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def _loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                self.run_due()
            except Exception:
                pass
            time.sleep(self._check_interval)

    def get_stats(self) -> Dict:
        """Return scheduler statistics."""
        return {
            "total_schedules": len(self.schedules),
            "enabled": sum(1 for s in self.schedules.values() if s.enabled),
            "pending": sum(1 for s in self.schedules.values() if s.state == ScheduleState.PENDING),
            "running": sum(1 for s in self.schedules.values() if s.state == ScheduleState.RUNNING),
            "completed": sum(1 for s in self.schedules.values() if s.state == ScheduleState.COMPLETED),
            "failed": sum(1 for s in self.schedules.values() if s.state == ScheduleState.FAILED),
            "is_running": self._running,
        }
