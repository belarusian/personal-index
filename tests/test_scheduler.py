"""Tests for personal_index.scheduler."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from personal_index.scheduler import (
    ScheduleConfig,
    ScheduleEntry,
    ScheduleStore,
    Scheduler,
)
from personal_index.interest_store import InterestStore
from personal_index.models import Interest, InterestType
from personal_index.search_index import SearchIndex


@pytest.fixture
def schedule_store_path(tmp_path):
    return str(tmp_path / "schedules.json")


@pytest.fixture
def store(schedule_store_path):
    return ScheduleStore(path=schedule_store_path)


@pytest.fixture
def interest_store(tmp_path):
    s = InterestStore(storage_path=str(tmp_path / "interests.json"))
    s.add(Interest("Py", InterestType.KEYWORD, "python", 5))
    return s


@pytest.fixture
def search_index(tmp_path):
    return SearchIndex(index_path=str(tmp_path / "index.json"))


@pytest.fixture
def scheduler(interest_store, search_index, schedule_store_path):
    schedule_store = ScheduleStore(path=schedule_store_path)
    return Scheduler(
        interest_store=interest_store,
        search_index=search_index,
        schedule_store=schedule_store,
    )


class TestScheduleConfig:
    """Tests for ScheduleConfig."""

    def test_defaults(self):
        config = ScheduleConfig()
        assert config.interval_hours == 24
        assert config.enabled is True
        assert config.seed_urls == []
        assert config.max_pages_per_run == 50
        assert config.crawl_depth == 2
        assert config.delay == 1.0

    def test_custom_config(self):
        config = ScheduleConfig(
            interval_hours=6,
            seed_urls=["https://example.com"],
            max_pages_per_run=200,
        )
        assert config.interval_hours == 6
        assert config.seed_urls == ["https://example.com"]
        assert config.max_pages_per_run == 200


class TestScheduleEntry:
    """Tests for ScheduleEntry."""

    def test_create_entry(self):
        config = ScheduleConfig(seed_urls=["https://example.com"])
        entry = ScheduleEntry(name="daily", config=config)
        assert entry.name == "daily"
        assert entry.run_count == 0
        assert entry.total_pages_indexed == 0
        assert entry.last_run is None
        assert entry.next_run is None


class TestScheduleStore:
    """Tests for ScheduleStore."""

    def test_empty_store(self, store):
        assert store.list_all() == []

    def test_add_entry(self, store):
        config = ScheduleConfig(seed_urls=["https://example.com"])
        entry = ScheduleEntry(name="daily", config=config)
        store.add(entry)
        assert len(store.list_all()) == 1

    def test_get_entry(self, store):
        config = ScheduleConfig(seed_urls=["https://example.com"])
        entry = ScheduleEntry(name="daily", config=config)
        store.add(entry)
        found = store.get("daily")
        assert found is not None
        assert found.name == "daily"

    def test_get_nonexistent(self, store):
        assert store.get("nonexistent") is None

    def test_remove_entry(self, store):
        config = ScheduleConfig(seed_urls=["https://example.com"])
        entry = ScheduleEntry(name="daily", config=config)
        store.add(entry)
        assert store.remove("daily") is True
        assert len(store.list_all()) == 0

    def test_remove_nonexistent(self, store):
        assert store.remove("nonexistent") is False

    def test_update_entry(self, store):
        config = ScheduleConfig(seed_urls=["https://example.com"])
        entry = ScheduleEntry(name="daily", config=config)
        store.add(entry)
        entry.run_count = 5
        store.update(entry)
        assert store.get("daily").run_count == 5

    def test_persistence(self, schedule_store_path):
        store1 = ScheduleStore(path=schedule_store_path)
        config = ScheduleConfig(seed_urls=["https://example.com"])
        entry = ScheduleEntry(name="daily", config=config)
        store1.add(entry)

        store2 = ScheduleStore(path=schedule_store_path)
        assert len(store2.list_all()) == 1
        assert store2.get("daily").config.seed_urls == ["https://example.com"]

    def test_persistence_with_timestamps(self, schedule_store_path):
        store1 = ScheduleStore(path=schedule_store_path)
        config = ScheduleConfig(seed_urls=["https://example.com"])
        entry = ScheduleEntry(
            name="daily",
            config=config,
            last_run=datetime(2024, 1, 1, 12, 0),
            next_run=datetime(2024, 1, 2, 12, 0),
        )
        store1.add(entry)

        store2 = ScheduleStore(path=schedule_store_path)
        loaded = store2.get("daily")
        assert loaded.last_run == datetime(2024, 1, 1, 12, 0)
        assert loaded.next_run == datetime(2024, 1, 2, 12, 0)


class TestScheduler:
    """Tests for Scheduler."""

    def test_add_schedule(self, scheduler):
        entry = scheduler.add_schedule(
            name="daily-python",
            seed_urls=["https://example.com"],
            interval_hours=24,
        )
        assert entry.name == "daily-python"
        assert entry.config.interval_hours == 24

    def test_remove_schedule(self, scheduler):
        scheduler.add_schedule("test", ["https://example.com"])
        assert scheduler.remove_schedule("test") is True

    def test_toggle_schedule(self, scheduler):
        scheduler.add_schedule("test", ["https://example.com"])
        entry = scheduler.toggle_schedule("test")
        assert entry is not None
        assert entry.config.enabled is False

    def test_get_due_schedules_none_due(self, scheduler):
        scheduler.add_schedule("test", ["https://example.com"])
        entry = scheduler.schedule_store.get("test")
        entry.next_run = datetime.now(timezone.utc) + timedelta(hours=100)
        scheduler.schedule_store.update(entry)
        due = scheduler.get_due_schedules()
        assert len(due) == 0

    def test_get_due_schedules_due(self, scheduler):
        scheduler.add_schedule("test", ["https://example.com"])
        entry = scheduler.schedule_store.get("test")
        entry.next_run = datetime.now(timezone.utc) - timedelta(hours=1)
        scheduler.schedule_store.update(entry)
        due = scheduler.get_due_schedules()
        assert len(due) == 1

    def test_get_due_schedules_disabled(self, scheduler):
        scheduler.add_schedule("test", ["https://example.com"])
        entry = scheduler.schedule_store.get("test")
        entry.config.enabled = False
        entry.next_run = datetime.now(timezone.utc) - timedelta(hours=1)
        scheduler.schedule_store.update(entry)
        due = scheduler.get_due_schedules()
        assert len(due) == 0

    def test_update_next_run_times(self, scheduler):
        scheduler.add_schedule("test", ["https://example.com"])
        entry = scheduler.schedule_store.get("test")
        entry.last_run = datetime(2024, 1, 1, 12, 0)
        scheduler.schedule_store.update(entry)

        scheduler.update_next_run_times()
        updated = scheduler.schedule_store.get("test")
        assert updated.next_run == datetime(2024, 1, 2, 12, 0)

    def test_run_schedule_disabled(self, scheduler):
        scheduler.add_schedule("test", ["https://example.com"])
        entry = scheduler.schedule_store.get("test")
        entry.config.enabled = False
        scheduler.schedule_store.update(entry)
        count = scheduler.run_schedule("test")
        assert count == 0

    def test_run_schedule_nonexistent(self, scheduler):
        count = scheduler.run_schedule("nonexistent")
        assert count == 0
