"""
Scheduled crawling for personal-index.

Manages periodic re-scanning of tracked topics using a background scheduler.
"""

import asyncio
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable
from pathlib import Path

from personal_index.config import ScheduleConfig
from personal_index.crawler import WebCrawler


@dataclass
class ScheduledJob:
    """A scheduled crawling job."""
    name: str
    seed_urls: list[str]
    interval_hours: int
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    enabled: bool = True
    run_count: int = 0
    status: str = "pending"  # pending, running, completed, failed
    error: Optional[str] = None


@dataclass
class SchedulerStats:
    """Statistics for the scheduler."""
    total_runs: int = 0
    total_pages_crawled: int = 0
    total_errors: int = 0
    last_run_time: Optional[str] = None


class Scheduler:
    """Manages scheduled crawling jobs."""

    def __init__(
        self,
        config: Optional[ScheduleConfig] = None,
        crawler: Optional[WebCrawler] = None,
        jobs_file: Optional[str] = None,
    ):
        self.config = config or ScheduleConfig()
        self.crawler = crawler
        self._jobs: dict[str, ScheduledJob] = {}
        self._stats = SchedulerStats()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._jobs_file = jobs_file
        self._callbacks: list[Callable] = []
        self._load_jobs()

    @property
    def stats(self) -> SchedulerStats:
        return self._stats

    def add_callback(self, callback: Callable) -> None:
        """Add a callback to be called after each scheduled run."""
        self._callbacks.append(callback)

    def add_job(self, job: ScheduledJob) -> None:
        """Add a scheduled job."""
        with self._lock:
            self._jobs[job.name] = job
            self._save_jobs()

    def remove_job(self, name: str) -> bool:
        """Remove a scheduled job by name."""
        with self._lock:
            if name in self._jobs:
                del self._jobs[name]
                self._save_jobs()
                return True
            return False

    def get_job(self, name: str) -> Optional[ScheduledJob]:
        """Get a job by name."""
        return self._jobs.get(name)

    def list_jobs(self) -> list[ScheduledJob]:
        """List all scheduled jobs."""
        return list(self._jobs.values())

    def enable_job(self, name: str) -> bool:
        """Enable a job."""
        job = self._jobs.get(name)
        if job:
            job.enabled = True
            self._save_jobs()
            return True
        return False

    def disable_job(self, name: str) -> bool:
        """Disable a job."""
        job = self._jobs.get(name)
        if job:
            job.enabled = False
            self._save_jobs()
            return True
        return False

    async def run_job(self, name: str) -> dict:
        """Run a specific job immediately."""
        job = self._jobs.get(name)
        if not job:
            return {"error": f"Job '{name}' not found"}

        if not self.crawler:
            return {"error": "No crawler configured"}

        job.status = "running"
        job.last_run = datetime.utcnow().isoformat()

        try:
            pages = await self.crawler.crawl(job.seed_urls)
            job.status = "completed"
            job.run_count += 1
            job.next_run = self._calculate_next_run(job.interval_hours)
            self._stats.total_runs += 1
            self._stats.total_pages_crawled += len(pages)
            self._stats.last_run_time = job.last_run

            for callback in self._callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(job, pages)
                    else:
                        callback(job, pages)
                except Exception:
                    pass

            self._save_jobs()
            return {
                "status": "completed",
                "pages_crawled": len(pages),
                "job_stats": self.crawler.stats,
            }
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            self._stats.total_errors += 1
            self._save_jobs()
            return {"status": "failed", "error": str(e)}

    def start(self) -> None:
        """Start the scheduler in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def _run_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            if self.config.enabled:
                now = time.monotonic()
                jobs_to_run = []
                with self._lock:
                    for job in self._jobs.values():
                        if job.enabled and self._is_due(job):
                            jobs_to_run.append(job.name)

                for job_name in jobs_to_run:
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        result = loop.run_until_complete(self.run_job(job_name))
                        loop.close()
                    except Exception:
                        pass

            time.sleep(60)  # Check every minute

    def _is_due(self, job: ScheduledJob) -> bool:
        """Check if a job is due to run."""
        if not job.next_run:
            return True
        try:
            next_run = datetime.fromisoformat(job.next_run)
            return datetime.utcnow() >= next_run
        except (ValueError, TypeError):
            return True

    def _calculate_next_run(self, interval_hours: int) -> str:
        """Calculate the next run time."""
        from datetime import timedelta
        next_run = datetime.utcnow() + timedelta(hours=interval_hours)
        return next_run.isoformat()

    def _get_jobs_file_path(self) -> str:
        """Get the path to the jobs file."""
        if self._jobs_file:
            return self._jobs_file
        config_dir = Path.home() / ".config" / "personal-index"
        return str(config_dir / "jobs.json")

    def _load_jobs(self) -> None:
        """Load jobs from file."""
        import json
        path = Path(self._get_jobs_file_path())
        if path.exists():
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                for name, job_data in data.items():
                    job = ScheduledJob(
                        name=job_data.get("name", name),
                        seed_urls=job_data.get("seed_urls", []),
                        interval_hours=job_data.get("interval_hours", 24),
                        last_run=job_data.get("last_run"),
                        next_run=job_data.get("next_run"),
                        enabled=job_data.get("enabled", True),
                        run_count=job_data.get("run_count", 0),
                        status=job_data.get("status", "pending"),
                        error=job_data.get("error"),
                    )
                    self._jobs[name] = job
            except (json.JSONDecodeError, KeyError):
                pass

    def _save_jobs(self) -> None:
        """Save jobs to file."""
        import json
        path = Path(self._get_jobs_file_path())
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            data = {}
            for name, job in self._jobs.items():
                data[name] = {
                    "name": job.name,
                    "seed_urls": job.seed_urls,
                    "interval_hours": job.interval_hours,
                    "last_run": job.last_run,
                    "next_run": job.next_run,
                    "enabled": job.enabled,
                    "run_count": job.run_count,
                    "status": job.status,
                    "error": job.error,
                }
            json.dump(data, f, indent=2)
