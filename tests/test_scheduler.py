"""Tests for the scheduler module."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from personal_index.scheduler import Scheduler, ScheduledJob, SchedulerStats
from personal_index.config import ScheduleConfig


class TestScheduledJob:
    def test_create_job(self):
        job = ScheduledJob(
            name="daily-news",
            seed_urls=["https://news.example.com"],
            interval_hours=24,
        )
        assert job.name == "daily-news"
        assert job.enabled is True
        assert job.status == "pending"
        assert job.run_count == 0

    def test_job_with_custom_values(self):
        job = ScheduledJob(
            name="tech",
            seed_urls=["https://tech.example.com"],
            interval_hours=6,
            enabled=False,
        )
        assert job.enabled is False
        assert job.interval_hours == 6


class TestSchedulerStats:
    def test_default_stats(self):
        stats = SchedulerStats()
        assert stats.total_runs == 0
        assert stats.total_pages_crawled == 0
        assert stats.total_errors == 0


class TestScheduler:
    def test_create_scheduler(self):
        scheduler = Scheduler()
        assert len(scheduler.list_jobs()) == 0
        assert scheduler.stats.total_runs == 0

    def test_add_job(self, tmp_path):
        jobs_file = str(tmp_path / "jobs.json")
        scheduler = Scheduler(jobs_file=jobs_file)
        job = ScheduledJob(
            name="test-job",
            seed_urls=["https://example.com"],
            interval_hours=12,
        )
        scheduler.add_job(job)
        assert len(scheduler.list_jobs()) == 1
        assert scheduler.get_job("test-job") is not None

    def test_remove_job(self, tmp_path):
        jobs_file = str(tmp_path / "jobs.json")
        scheduler = Scheduler(jobs_file=jobs_file)
        scheduler.add_job(ScheduledJob(
            name="test-job",
            seed_urls=["https://example.com"],
            interval_hours=12,
        ))
        assert scheduler.remove_job("test-job") is True
        assert len(scheduler.list_jobs()) == 0

    def test_remove_nonexistent_job(self, tmp_path):
        jobs_file = str(tmp_path / "jobs.json")
        scheduler = Scheduler(jobs_file=jobs_file)
        assert scheduler.remove_job("nonexistent") is False

    def test_enable_job(self, tmp_path):
        jobs_file = str(tmp_path / "jobs.json")
        scheduler = Scheduler(jobs_file=jobs_file)
        scheduler.add_job(ScheduledJob(
            name="test-job",
            seed_urls=["https://example.com"],
            interval_hours=12,
            enabled=False,
        ))
        assert scheduler.enable_job("test-job") is True
        assert scheduler.get_job("test-job").enabled is True

    def test_disable_job(self, tmp_path):
        jobs_file = str(tmp_path / "jobs.json")
        scheduler = Scheduler(jobs_file=jobs_file)
        scheduler.add_job(ScheduledJob(
            name="test-job",
            seed_urls=["https://example.com"],
            interval_hours=12,
            enabled=True,
        ))
        assert scheduler.disable_job("test-job") is True
        assert scheduler.get_job("test-job").enabled is False

    def test_job_persistence(self, tmp_path):
        jobs_file = str(tmp_path / "jobs.json")
        scheduler = Scheduler(jobs_file=jobs_file)
        scheduler.add_job(ScheduledJob(
            name="persistent-job",
            seed_urls=["https://example.com"],
            interval_hours=6,
        ))

        scheduler2 = Scheduler(jobs_file=jobs_file)
        assert len(scheduler2.list_jobs()) == 1
        assert scheduler2.get_job("persistent-job").interval_hours == 6

    def test_run_job_no_crawler(self, tmp_path):
        jobs_file = str(tmp_path / "jobs.json")
        scheduler = Scheduler(jobs_file=jobs_file)
        scheduler.add_job(ScheduledJob(
            name="test-job",
            seed_urls=["https://example.com"],
            interval_hours=12,
        ))
        import asyncio
        result = asyncio.run(scheduler.run_job("test-job"))
        assert "error" in result

    def test_run_nonexistent_job(self, tmp_path):
        jobs_file = str(tmp_path / "jobs.json")
        scheduler = Scheduler(jobs_file=jobs_file)
        import asyncio
        result = asyncio.run(scheduler.run_job("nonexistent"))
        assert "error" in result

    def test_calculate_next_run(self):
        scheduler = Scheduler()
        next_run = scheduler._calculate_next_run(24)
        assert next_run is not None
        assert len(next_run) > 0

    def test_is_due_no_next_run(self):
        scheduler = Scheduler()
        job = ScheduledJob(name="test", seed_urls=[], interval_hours=1)
        assert scheduler._is_due(job) is True

    def test_is_due_with_past_next_run(self):
        scheduler = Scheduler()
        job = ScheduledJob(
            name="test",
            seed_urls=[],
            interval_hours=1,
            next_run="2020-01-01T00:00:00",
        )
        assert scheduler._is_due(job) is True

    def test_add_callback(self):
        scheduler = Scheduler()
        callback_called = []
        def my_callback(job, pages):
            callback_called.append(True)
        scheduler.add_callback(my_callback)
        assert len(scheduler._callbacks) == 1

    def test_list_jobs_empty(self, tmp_path):
        jobs_file = str(tmp_path / "jobs.json")
        scheduler = Scheduler(jobs_file=jobs_file)
        assert scheduler.list_jobs() == []

    def test_multiple_jobs(self, tmp_path):
        jobs_file = str(tmp_path / "jobs.json")
        scheduler = Scheduler(jobs_file=jobs_file)
        scheduler.add_job(ScheduledJob(name="job1", seed_urls=["https://a.com"], interval_hours=12))
        scheduler.add_job(ScheduledJob(name="job2", seed_urls=["https://b.com"], interval_hours=6))
        assert len(scheduler.list_jobs()) == 2
