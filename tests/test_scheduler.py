"""Tests for personal_index.scheduler."""

import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from personal_index.models import CrawlConfig, CrawlStats
from personal_index.scheduler import (
    CrawlSchedule,
    CrawlJob,
    CrawlScheduler,
)


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for scheduler data."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def scheduler(temp_data_dir):
    """Create a CrawlScheduler with a temp directory."""
    return CrawlScheduler(data_dir=temp_data_dir)


class TestCrawlSchedule:
    def test_create_schedule(self):
        schedule = CrawlSchedule(topic="python", interval_hours=24.0)
        assert schedule.topic == "python"
        assert schedule.interval_hours == 24.0
        assert schedule.enabled is True
        assert schedule.last_run is None

    def test_is_due_no_next_run(self):
        schedule = CrawlSchedule(topic="python")
        assert schedule.is_due() is True

    def test_is_due_past_next_run(self):
        schedule = CrawlSchedule(
            topic="python",
            next_run=datetime.utcnow() - timedelta(hours=1),
        )
        assert schedule.is_due() is True

    def test_is_due_future_next_run(self):
        schedule = CrawlSchedule(
            topic="python",
            next_run=datetime.utcnow() + timedelta(hours=1),
        )
        assert schedule.is_due() is False

    def test_is_due_when_disabled(self):
        schedule = CrawlSchedule(
            topic="python",
            enabled=False,
            next_run=datetime.utcnow() - timedelta(hours=1),
        )
        assert schedule.is_due() is False

    def test_mark_run(self):
        schedule = CrawlSchedule(topic="python", interval_hours=24.0)
        schedule.mark_run()
        assert schedule.last_run is not None
        assert schedule.next_run is not None
        expected_next = schedule.last_run + timedelta(hours=24.0)
        assert abs((schedule.next_run - expected_next).total_seconds()) < 1


class TestCrawlJob:
    def test_create_job(self):
        job = CrawlJob(job_id="test-1", topic="python")
        assert job.job_id == "test-1"
        assert job.topic == "python"
        assert job.status == "pending"
        assert job.pages_crawled == 0

    def test_job_status_transitions(self):
        job = CrawlJob(job_id="test-1", topic="python")
        job.status = "running"
        assert job.status == "running"
        job.status = "completed"
        assert job.status == "completed"


class TestCrawlScheduler:
    def test_add_schedule(self, scheduler):
        schedule = scheduler.add_schedule("python", interval_hours=12.0)
        assert schedule.topic == "python"
        assert schedule.interval_hours == 12.0

    def test_add_schedule_with_config(self, scheduler):
        config = CrawlConfig(max_depth=3, max_pages=200)
        schedule = scheduler.add_schedule("python", config=config)
        assert schedule.config.max_depth == 3
        assert schedule.config.max_pages == 200

    def test_list_schedules(self, scheduler):
        scheduler.add_schedule("python", interval_hours=12.0)
        scheduler.add_schedule("ai", interval_hours=6.0)
        schedules = scheduler.list_schedules()
        assert len(schedules) == 2

    def test_remove_schedule(self, scheduler):
        scheduler.add_schedule("python")
        assert scheduler.remove_schedule("python") is True
        assert scheduler.remove_schedule("python") is False

    def test_get_schedule(self, scheduler):
        scheduler.add_schedule("python")
        schedule = scheduler.get_schedule("python")
        assert schedule is not None
        assert schedule.topic == "python"

    def test_get_nonexistent_schedule(self, scheduler):
        assert scheduler.get_schedule("nonexistent") is None

    def test_toggle_schedule(self, scheduler):
        scheduler.add_schedule("python")
        schedule = scheduler.toggle_schedule("python")
        assert schedule.enabled is False
        schedule = scheduler.toggle_schedule("python")
        assert schedule.enabled is True

    def test_persistence(self, temp_data_dir):
        """Test that schedules persist across instances."""
        scheduler1 = CrawlScheduler(data_dir=temp_data_dir)
        scheduler1.add_schedule("python", interval_hours=12.0)

        scheduler2 = CrawlScheduler(data_dir=temp_data_dir)
        schedules = scheduler2.list_schedules()
        assert len(schedules) == 1
        assert schedules[0].topic == "python"

    def test_run_now_without_callback(self, scheduler):
        scheduler.add_schedule("python")
        job = scheduler.run_now("python")
        assert job is None

    def test_run_now_with_callback(self, scheduler):
        scheduler.add_schedule("python")

        mock_stats = CrawlStats(
            pages_crawled=10,
            pages_stored=5,
            errors=0,
        )
        scheduler.set_crawl_callback(lambda s: mock_stats)
        job = scheduler.run_now("python")

        assert job is not None
        assert job.status == "completed"
        assert job.pages_crawled == 10
        assert job.pages_stored == 5

    def test_run_now_with_failing_callback(self, scheduler):
        scheduler.add_schedule("python")
        scheduler.set_crawl_callback(lambda s: 1 / 0)
        job = scheduler.run_now("python")

        assert job is not None
        assert job.status == "failed"
        assert job.error_message is not None

    def test_run_now_nonexistent_topic(self, scheduler):
        scheduler.set_crawl_callback(lambda s: CrawlStats())
        job = scheduler.run_now("nonexistent")
        assert job is None

    def test_list_jobs(self, scheduler):
        scheduler.add_schedule("python")
        scheduler.set_crawl_callback(lambda s: CrawlStats(pages_crawled=5))
        scheduler.run_now("python")
        jobs = scheduler.list_jobs()
        assert len(jobs) >= 1

    def test_get_job(self, scheduler):
        scheduler.add_schedule("python")
        scheduler.set_crawl_callback(lambda s: CrawlStats())
        job = scheduler.run_now("python")
        retrieved = scheduler.get_job(job.job_id)
        assert retrieved is not None
        assert retrieved.job_id == job.job_id

    def test_run_now_nonexistent_topic(self, scheduler):
        job = scheduler.run_now("nonexistent")
        assert job is None
