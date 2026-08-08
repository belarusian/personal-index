"""Tests for scheduler module."""

import pytest
import time
from datetime import datetime, timezone, timedelta
from personal_index.config import AppConfig
from personal_index.scheduler import CrawlScheduler, ScheduleEntry


class TestScheduleEntry:
    def test_creation(self):
        entry = ScheduleEntry(name="daily crawl", interval_hours=24)
        assert entry.name == "daily crawl"
        assert entry.interval_hours == 24
        assert entry.enabled is True

    def test_to_dict(self):
        entry = ScheduleEntry(
            name="test",
            interval_hours=12,
            seed_urls=["http://example.com"],
            topics=["AI"],
        )
        d = entry.to_dict()
        assert d["name"] == "test"
        assert d["interval_hours"] == 12
        assert d["seed_urls"] == ["http://example.com"]

    def test_from_dict(self):
        data = {
            "name": "test",
            "interval_hours": 12,
            "last_run": None,
            "next_run": None,
            "enabled": True,
            "seed_urls": ["http://example.com"],
            "topics": ["AI"],
        }
        entry = ScheduleEntry.from_dict(data)
        assert entry.name == "test"
        assert entry.interval_hours == 12


class TestCrawlScheduler:
    def test_creation(self):
        scheduler = CrawlScheduler()
        assert len(scheduler.entries) == 0
        assert scheduler._running is False

    def test_add_schedule(self):
        scheduler = CrawlScheduler()
        entry = scheduler.add_schedule("daily", interval_hours=24)
        assert len(scheduler.entries) == 1
        assert entry.name == "daily"
        assert entry.interval_hours == 24

    def test_add_schedule_with_urls(self):
        scheduler = CrawlScheduler()
        entry = scheduler.add_schedule(
            "news",
            interval_hours=6,
            seed_urls=["http://news.example.com"],
            topics=["news"],
        )
        assert entry.seed_urls == ["http://news.example.com"]
        assert entry.topics == ["news"]

    def test_remove_schedule(self):
        scheduler = CrawlScheduler()
        scheduler.add_schedule("daily")
        removed = scheduler.remove_schedule("daily")
        assert removed is True
        assert len(scheduler.entries) == 0

    def test_remove_nonexistent_schedule(self):
        scheduler = CrawlScheduler()
        removed = scheduler.remove_schedule("nonexistent")
        assert removed is False

    def test_enable_schedule(self):
        scheduler = CrawlScheduler()
        entry = scheduler.add_schedule("daily")
        entry.enabled = False
        enabled = scheduler.enable_schedule("daily")
        assert enabled is True
        assert entry.enabled is True

    def test_disable_schedule(self):
        scheduler = CrawlScheduler()
        entry = scheduler.add_schedule("daily")
        disabled = scheduler.disable_schedule("daily")
        assert disabled is True
        assert entry.enabled is False

    def test_get_schedule(self):
        scheduler = CrawlScheduler()
        scheduler.add_schedule("daily")
        entry = scheduler.get_schedule("daily")
        assert entry is not None
        assert entry.name == "daily"

    def test_get_nonexistent_schedule(self):
        scheduler = CrawlScheduler()
        entry = scheduler.get_schedule("nonexistent")
        assert entry is None

    def test_list_schedules(self):
        scheduler = CrawlScheduler()
        scheduler.add_schedule("daily")
        scheduler.add_schedule("hourly")
        schedules = scheduler.list_schedules()
        assert len(schedules) == 2

    def test_run_due_first_run(self):
        scheduler = CrawlScheduler()
        scheduler.add_schedule("daily", seed_urls=["http://example.com"])
        executed = []

        def callback(entry):
            executed.append(entry.name)

        scheduler.set_crawl_callback(callback)
        result = scheduler.run_due()
        assert "daily" in result
        assert "daily" in executed

    def test_run_due_not_yet(self):
        scheduler = CrawlScheduler()
        entry = scheduler.add_schedule("daily", interval_hours=24)
        # Set last_run to now
        entry.last_run = datetime.now(timezone.utc).isoformat()
        executed = []

        def callback(entry):
            executed.append(entry.name)

        scheduler.set_crawl_callback(callback)
        result = scheduler.run_due()
        assert len(result) == 0
        assert len(executed) == 0

    def test_run_due_disabled(self):
        scheduler = CrawlScheduler()
        entry = scheduler.add_schedule("daily")
        entry.enabled = False
        executed = []

        def callback(entry):
            executed.append(entry.name)

        scheduler.set_crawl_callback(callback)
        result = scheduler.run_due()
        assert len(result) == 0

    def test_run_due_multiple(self):
        scheduler = CrawlScheduler()
        scheduler.add_schedule("daily", interval_hours=24)
        scheduler.add_schedule("hourly", interval_hours=1)
        executed = []

        def callback(entry):
            executed.append(entry.name)

        scheduler.set_crawl_callback(callback)
        result = scheduler.run_due()
        assert len(result) == 2
        assert "daily" in executed
        assert "hourly" in executed

    def test_run_due_callback_error(self):
        scheduler = CrawlScheduler()
        scheduler.add_schedule("daily")

        def bad_callback(entry):
            raise ValueError("test error")

        scheduler.set_crawl_callback(bad_callback)
        result = scheduler.run_due()
        assert len(result) == 0

    def test_start_stop(self):
        scheduler = CrawlScheduler()
        scheduler.start(poll_interval=1)
        assert scheduler.is_running() is True
        time.sleep(0.1)
        scheduler.stop()
        assert scheduler.is_running() is False

    def test_start_already_running(self):
        scheduler = CrawlScheduler()
        scheduler.start(poll_interval=1)
        scheduler.start(poll_interval=1)
        assert scheduler.is_running() is True
        scheduler.stop()

    def test_get_stats(self):
        scheduler = CrawlScheduler()
        scheduler.add_schedule("daily")
        scheduler.add_schedule("hourly")
        scheduler.disable_schedule("hourly")
        stats = scheduler.get_stats()
        assert stats["total_schedules"] == 2
        assert stats["enabled"] == 1
        assert stats["disabled"] == 1
        assert stats["running"] is False
