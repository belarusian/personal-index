"""Integration tests for scheduler functionality."""

from __future__ import annotations

import os
import tempfile

import pytest

from personal_index.app import PersonalIndexApp
from personal_index.scheduler import ScheduleConfig, Scheduler, ScheduleStore


class TestSchedulerIntegration:
    """Test scheduler end-to-end."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.app = PersonalIndexApp(
            config_path=os.path.join(self.tmpdir, "config.yaml"),
            data_dir=os.path.join(self.tmpdir, "data"),
        )
        self.app.initialize()

    def test_add_scheduled_job(self):
        """Adding a scheduled job should work."""
        self.app.scheduler.add_job(name="daily-crawl", seed_urls=["https://example.com"], interval_hours=24)
        jobs = self.app.scheduler.list_jobs()
        assert len(jobs) == 1
        assert jobs[0].name == "daily-crawl"

    def test_add_multiple_jobs(self):
        """Adding multiple jobs should accumulate."""
        self.app.scheduler.add_job(name="job1", seed_urls=["https://a.com"], interval_hours=12)
        self.app.scheduler.add_job(name="job2", seed_urls=["https://b.com"], interval_hours=24)
        jobs = self.app.scheduler.list_jobs()
        assert len(jobs) == 2

    def test_remove_job(self):
        """Removing a job should work."""
        self.app.scheduler.add_job(name="temp", seed_urls=["https://x.com"], interval_hours=6)
        assert len(self.app.scheduler.list_jobs()) == 1
        self.app.scheduler.remove_job("temp")
        assert len(self.app.scheduler.list_jobs()) == 0

    def test_remove_nonexistent_job(self):
        """Removing a nonexistent job should return False."""
        assert self.app.scheduler.remove_job("nonexistent") is False

    def test_job_persistence(self):
        """Jobs should persist across reloads."""
        self.app.scheduler.add_job(name="persist", seed_urls=["https://p.com"], interval_hours=48)
        schedule_path = os.path.join(self.app.data_dir, "schedules.json")
        new_store = ScheduleStore(path=schedule_path)
        new_scheduler = Scheduler(
            interest_store=self.app.interest_store,
            search_index=self.app.search_index,
            schedule_store=new_store,
        )
        jobs = new_scheduler.list_jobs()
        assert len(jobs) >= 1
        assert any(j.name == "persist" for j in jobs)

    def test_empty_scheduler(self):
        """New scheduler should have no jobs."""
        jobs = self.app.scheduler.list_jobs()
        assert jobs == []
