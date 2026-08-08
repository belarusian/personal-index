"""Scheduled crawling for personal-index.

Handles periodic re-scanning of tracked topics with configurable
schedules and crawl management.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

from personal_index.models import CrawlConfig, CrawlStats, Interest

logger = logging.getLogger(__name__)


@dataclass
class CrawlSchedule:
    """Defines when and how often to crawl."""

    topic: str
    interval_hours: float = 24.0
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    enabled: bool = True
    config: Optional[CrawlConfig] = None

    def is_due(self) -> bool:
        """Check if this schedule is due for execution."""
        if not self.enabled:
            return False
        if self.next_run is None:
            return True
        return datetime.utcnow() >= self.next_run

    def mark_run(self) -> None:
        """Mark this schedule as having just run."""
        self.last_run = datetime.utcnow()
        self.next_run = self._calculate_next_run()

    def _calculate_next_run(self) -> datetime:
        """Calculate when the next run should happen."""
        return self.last_run + timedelta(hours=self.interval_hours)


@dataclass
class CrawlJob:
    """Represents a single crawl job."""

    job_id: str
    topic: str
    status: str = "pending"  # pending, running, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    pages_crawled: int = 0
    pages_stored: int = 0
    errors: int = 0
    error_message: Optional[str] = None


class CrawlScheduler:
    """Manages scheduled crawling of tracked topics."""

    def __init__(self, data_dir: str = "~/.personal-index"):
        self.data_dir = Path(data_dir).expanduser()
        self.schedules_file = self.data_dir / "schedules.json"
        self.jobs_file = self.data_dir / "jobs.json"
        self._schedules: dict[str, CrawlSchedule] = {}
        self._jobs: dict[str, CrawlJob] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._crawl_callback: Optional[Callable] = None
        self._load_state()

    def _load_state(self) -> None:
        """Load schedules and jobs from disk."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if self.schedules_file.exists():
            try:
                with open(self.schedules_file, "r") as f:
                    data = json.load(f)
                for key, sched_data in data.get("schedules", {}).items():
                    config = None
                    if sched_data.get("config"):
                        config = CrawlConfig(**sched_data["config"])
                    sched = CrawlSchedule(
                        topic=sched_data["topic"],
                        interval_hours=sched_data.get("interval_hours", 24.0),
                        last_run=sched_data.get("last_run"),
                        next_run=sched_data.get("next_run"),
                        enabled=sched_data.get("enabled", True),
                        config=config,
                    )
                    self._schedules[key] = sched
            except (json.JSONDecodeError, KeyError):
                logger.warning("Failed to load schedules, starting fresh")

        if self.jobs_file.exists():
            try:
                with open(self.jobs_file, "r") as f:
                    data = json.load(f)
                for key, job_data in data.get("jobs", {}).items():
                    job = CrawlJob(
                        job_id=key,
                        topic=job_data["topic"],
                        status=job_data.get("status", "pending"),
                        started_at=job_data.get("started_at"),
                        completed_at=job_data.get("completed_at"),
                        pages_crawled=job_data.get("pages_crawled", 0),
                        pages_stored=job_data.get("pages_stored", 0),
                        errors=job_data.get("errors", 0),
                        error_message=job_data.get("error_message"),
                    )
                    self._jobs[key] = job
            except (json.JSONDecodeError, KeyError):
                logger.warning("Failed to load jobs, starting fresh")

    def _save_state(self) -> None:
        """Save schedules and jobs to disk."""
        schedules_data = {}
        for key, sched in self._schedules.items():
            sched_dict = {
                "topic": sched.topic,
                "interval_hours": sched.interval_hours,
                "last_run": sched.last_run.isoformat() if sched.last_run else None,
                "next_run": sched.next_run.isoformat() if sched.next_run else None,
                "enabled": sched.enabled,
            }
            if sched.config:
                sched_dict["config"] = {
                    "max_depth": sched.config.max_depth,
                    "max_pages": sched.config.max_pages,
                    "rate_limit": sched.config.rate_limit,
                    "politeness_delay": sched.config.politeness_delay,
                    "timeout": sched.config.timeout,
                    "user_agent": sched.config.user_agent,
                    "respect_robots": sched.config.respect_robots,
                    "allowed_domains": sched.config.allowed_domains,
                    "blocked_domains": sched.config.blocked_domains,
                    "max_content_length": sched.config.max_content_length,
                }
            schedules_data[key] = sched_dict

        jobs_data = {}
        for key, job in self._jobs.items():
            jobs_data[key] = {
                "job_id": job.job_id,
                "topic": job.topic,
                "status": job.status,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "pages_crawled": job.pages_crawled,
                "pages_stored": job.pages_stored,
                "errors": job.errors,
                "error_message": job.error_message,
            }

        with open(self.schedules_file, "w") as f:
            json.dump({"schedules": schedules_data}, f, indent=2)
        with open(self.jobs_file, "w") as f:
            json.dump({"jobs": jobs_data}, f, indent=2)

    def add_schedule(
        self,
        topic: str,
        interval_hours: float = 24.0,
        config: Optional[CrawlConfig] = None,
    ) -> CrawlSchedule:
        """Add a new crawl schedule for a topic."""
        schedule = CrawlSchedule(
            topic=topic,
            interval_hours=interval_hours,
            config=config,
        )
        self._schedules[topic] = schedule
        self._save_state()
        logger.info(f"Added schedule for '{topic}' every {interval_hours}h")
        return schedule

    def remove_schedule(self, topic: str) -> bool:
        """Remove a crawl schedule."""
        if topic in self._schedules:
            del self._schedules[topic]
            self._save_state()
            return True
        return False

    def list_schedules(self) -> list[CrawlSchedule]:
        """List all crawl schedules."""
        return list(self._schedules.values())

    def get_schedule(self, topic: str) -> Optional[CrawlSchedule]:
        """Get a schedule by topic."""
        return self._schedules.get(topic)

    def toggle_schedule(self, topic: str) -> Optional[CrawlSchedule]:
        """Toggle a schedule's enabled status."""
        schedule = self._schedules.get(topic)
        if schedule:
            schedule.enabled = not schedule.enabled
            self._save_state()
        return schedule

    def set_crawl_callback(self, callback: Callable) -> None:
        """Set the callback function to execute when a crawl is due.

        The callback should accept a CrawlSchedule and return CrawlStats.
        """
        self._crawl_callback = callback

    def start(self) -> None:
        """Start the scheduler loop."""
        if self._running:
            logger.warning("Scheduler is already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Scheduler started")

    def stop(self) -> None:
        """Stop the scheduler loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        logger.info("Scheduler stopped")

    def _run_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            with self._lock:
                due_schedules = [s for s in self._schedules.values() if s.is_due()]

            for schedule in due_schedules:
                self._execute_schedule(schedule)

            time.sleep(60)  # Check every minute

    def _execute_schedule(self, schedule: CrawlSchedule) -> None:
        """Execute a due schedule."""
        if not self._crawl_callback:
            logger.warning(f"No crawl callback set, skipping '{schedule.topic}'")
            return

        job = CrawlJob(
            job_id=f"{schedule.topic}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            topic=schedule.topic,
            status="running",
            started_at=datetime.utcnow(),
        )
        self._jobs[job.job_id] = job
        self._save_state()

        try:
            logger.info(f"Running scheduled crawl for '{schedule.topic}'")
            stats = self._crawl_callback(schedule)
            job.status = "completed"
            job.pages_crawled = stats.pages_crawled
            job.pages_stored = stats.pages_stored
            job.errors = stats.errors
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            logger.error(f"Crawl failed for '{schedule.topic}': {e}")
        finally:
            job.completed_at = datetime.utcnow()
            schedule.mark_run()
            self._save_state()

    def run_now(self, topic: str) -> Optional[CrawlJob]:
        """Manually trigger a crawl for a topic."""
        schedule = self._schedules.get(topic)
        if not schedule:
            logger.warning(f"No schedule found for '{topic}'")
            return None

        if not self._crawl_callback:
            logger.warning("No crawl callback set")
            return None

        job = CrawlJob(
            job_id=f"{topic}-manual-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            topic=topic,
            status="running",
            started_at=datetime.utcnow(),
        )
        self._jobs[job.job_id] = job

        try:
            stats = self._crawl_callback(schedule)
            job.status = "completed"
            job.pages_crawled = stats.pages_crawled
            job.pages_stored = stats.pages_stored
            job.errors = stats.errors
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
        finally:
            job.completed_at = datetime.utcnow()
            self._save_state()

        return job

    def list_jobs(self, limit: int = 20) -> list[CrawlJob]:
        """List recent crawl jobs."""
        jobs = sorted(
            self._jobs.values(),
            key=lambda j: j.started_at or datetime.min,
            reverse=True,
        )
        return jobs[:limit]

    def get_job(self, job_id: str) -> Optional[CrawlJob]:
        """Get a job by ID."""
        return self._jobs.get(job_id)
