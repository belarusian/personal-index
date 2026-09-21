"""Tests for personal_index.scheduler."""

from datetime import datetime, timedelta, timezone

import pytest

from personal_index.interests import InterestStore
from personal_index.models import Interest, InterestType
from personal_index.scheduler import (
    ScheduleConfig,
    ScheduleEntry,
    Scheduler,
    ScheduleStore,
)
from personal_index.search_index import SearchIndex


@pytest.fixture
def schedule_store_path(tmp_path):
    return str(tmp_path / "schedules.json")


@pytest.fixture
def store(schedule_store_path):
    return ScheduleStore(path=schedule_store_path)


@pytest.fixture
def interest_store(tmp_path):
    s = InterestStore(store_path=str(tmp_path / "interests.json"))
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
            last_run=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            next_run=datetime(2024, 1, 2, 12, 0, tzinfo=timezone.utc),
        )
        store1.add(entry)

        store2 = ScheduleStore(path=schedule_store_path)
        loaded = store2.get("daily")
        assert loaded.last_run == datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert loaded.next_run == datetime(2024, 1, 2, 12, 0, tzinfo=timezone.utc)


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
        entry.last_run = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        scheduler.schedule_store.update(entry)

        scheduler.update_next_run_times()
        updated = scheduler.schedule_store.get("test")
        assert updated.next_run == datetime(2024, 1, 2, 12, 0, tzinfo=timezone.utc)

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

class TestScheduleStoreNonDictJSON:
    """Regression tests for TICKET-265: non-dict JSON in storage file."""

    def test_null_storage_resets_to_empty(self, tmp_path):
        path = str(tmp_path / "schedules.json")
        with open(path, "w") as f:
            f.write("null")
        store = ScheduleStore(path=path)
        assert store._entries == {}

    def test_list_storage_resets_to_empty(self, tmp_path):
        path = str(tmp_path / "schedules.json")
        with open(path, "w") as f:
            f.write("[1, 2, 3]")
        store = ScheduleStore(path=path)
        assert store._entries == {}

    def test_number_storage_resets_to_empty(self, tmp_path):
        path = str(tmp_path / "schedules.json")
        with open(path, "w") as f:
            f.write("42")
        store = ScheduleStore(path=path)
        assert store._entries == {}


class TestScheduleStoreCorruptTimestamp:
    """Regression tests for TICKET-312: corrupt last_run/next_run timestamp.

    The TICKET-265 guard degrades to an empty store on corrupt JSON / non-dict /
    missing keys, but datetime.fromisoformat raises ValueError on a corrupt
    timestamp string, which the guard must also catch.
    """

    def _write(self, path, last_run, next_run):
        import json

        with open(path, "w") as f:
            json.dump(
                {
                    "job1": {
                        "config": {
                            "interval_hours": 24,
                            "enabled": True,
                            "seed_urls": [],
                            "max_pages_per_run": 50,
                            "crawl_depth": 2,
                            "delay": 1.0,
                        },
                        "last_run": last_run,
                        "next_run": next_run,
                        "run_count": 0,
                        "total_pages_indexed": 0,
                    }
                },
                f,
            )

    def test_corrupt_last_run_degrades_to_empty(self, tmp_path):
        path = str(tmp_path / "schedules.json")
        self._write(path, last_run="not-a-timestamp", next_run=None)
        store = ScheduleStore(path=path)
        assert store._entries == {}

    def test_corrupt_next_run_degrades_to_empty(self, tmp_path):
        path = str(tmp_path / "schedules.json")
        self._write(path, last_run=None, next_run="bad")
        store = ScheduleStore(path=path)
        assert store._entries == {}

    def test_valid_timestamps_still_load(self, tmp_path):
        path = str(tmp_path / "schedules.json")
        self._write(
            path,
            last_run="2024-01-01T12:00:00+00:00",
            next_run="2024-01-02T12:00:00+00:00",
        )
        store = ScheduleStore(path=path)
        assert len(store._entries) == 1
        entry = store._entries["job1"]
        assert entry.last_run == datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert entry.next_run == datetime(2024, 1, 2, 12, 0, tzinfo=timezone.utc)


class TestScheduleStoreAtomicSave:
    """Regression tests for ARCH-104: _save must be atomic (temp + os.replace).

    A crash mid-write must not leave the target file truncated or empty, which
    _load would then silently read as an empty store and lose all entries.
    """

    def test_save_is_atomic_no_partial_file(self, tmp_path, monkeypatch):
        import json as _json

        path = str(tmp_path / "schedules.json")
        store1 = ScheduleStore(path=path)
        store1.add(
            ScheduleEntry(
                name="daily",
                config=ScheduleConfig(seed_urls=["https://example.com"]),
            )
        )
        with open(path) as f:
            good = f.read()
        assert good.strip() != "{}"

        # Simulate a crash mid-write: json.dump raises OSError.
        def boom(*a, **k):
            raise OSError("simulated crash mid-write")

        monkeypatch.setattr("personal_index.scheduler.json.dump", boom)
        with pytest.raises(OSError):
            store1.add(ScheduleEntry(name="nightly", config=ScheduleConfig()))

        # The target file must still hold the previous complete JSON.
        with open(path) as f:
            after = f.read()
        assert after == good
        data = _json.loads(after)
        assert "daily" in data
        assert "nightly" not in data

    def test_save_roundtrip_after_failed_save(self, tmp_path, monkeypatch):
        path = str(tmp_path / "schedules.json")
        store1 = ScheduleStore(path=path)
        store1.add(
            ScheduleEntry(
                name="daily",
                config=ScheduleConfig(seed_urls=["https://example.com"]),
            )
        )

        def boom(*a, **k):
            raise OSError("simulated crash mid-write")

        monkeypatch.setattr("personal_index.scheduler.json.dump", boom)
        with pytest.raises(OSError):
            store1.add(ScheduleEntry(name="nightly", config=ScheduleConfig()))

        # A fresh store must load the pre-failure entries, not empty.
        store2 = ScheduleStore(path=path)
        assert len(store2.list_all()) == 1
        assert store2.get("daily").config.seed_urls == ["https://example.com"]
        assert store2.get("nightly") is None


class TestScheduleStoreNaiveDatetime:
    """Regression tests for QA-52 (issue #1636): naive stored datetimes.

    A store file written by an external writer / older version may carry
    offset-NAIVE ISO timestamps for last_run/next_run. _load must normalize
    them to UTC so the public get_due_schedules() (which compares against an
    aware datetime.now(timezone.utc)) never raises TypeError.
    """

    def _write_naive(self, path):
        import json

        with open(path, "w") as f:
            json.dump(
                {
                    "job1": {
                        "config": {
                            "interval_hours": 24,
                            "enabled": True,
                            "seed_urls": [],
                            "max_pages_per_run": 50,
                            "crawl_depth": 2,
                            "delay": 1.0,
                        },
                        "last_run": "2024-01-01T12:00:00",
                        "next_run": "2024-01-02T12:00:00",
                        "run_count": 0,
                        "total_pages_indexed": 0,
                    }
                },
                f,
            )

    def test_naive_timestamps_normalized_to_utc(self, tmp_path):
        path = str(tmp_path / "schedules.json")
        self._write_naive(path)
        store = ScheduleStore(path=path)
        entry = store.get("job1")
        assert entry.last_run == datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert entry.next_run == datetime(2024, 1, 2, 12, 0, tzinfo=timezone.utc)

    def test_naive_next_run_does_not_crash_get_due(self, tmp_path):
        path = str(tmp_path / "schedules.json")
        self._write_naive(path)
        store = ScheduleStore(path=path)
        sch = Scheduler(
            interest_store=InterestStore(
                store_path=str(tmp_path / "interests.json")
            ),
            search_index=SearchIndex(index_path=str(tmp_path / "index.json")),
            schedule_store=store,
        )
        # A naive next_run in the past must be comparable and reported due.
        due = sch.get_due_schedules()
        assert [e.name for e in due] == ["job1"]


class TestScheduleStoreUnparseableTimestampPerEntry:
    """Regression tests for QA-58 (issue #1690): per-entry timestamp tolerance.

    _load must skip a single entry whose last_run/next_run timestamp is
    unparseable (e.g. an ISO-8601 "Z"-suffix, which datetime.fromisoformat
    rejects on Python < 3.11) WITHOUT wiping the whole store: valid sibling
    entries must survive a defensive load.
    """

    def _write(self, path, entries):
        import json

        with open(path, "w") as f:
            json.dump(entries, f)

    def _entry(self, last_run, next_run):
        return {
            "config": {
                "interval_hours": 24,
                "enabled": True,
                "seed_urls": [],
                "max_pages_per_run": 50,
                "crawl_depth": 2,
                "delay": 1.0,
            },
            "run_count": 0,
            "total_pages_indexed": 0,
            "last_run": last_run,
            "next_run": next_run,
        }

    def test_all_valid_entries_load(self, tmp_path):
        """Normal case: every entry with a parseable timestamp loads."""
        path = str(tmp_path / "schedules.json")
        self._write(
            path,
            {
                "a": self._entry(
                    "2024-01-01T12:00:00+00:00",
                    "2024-01-02T12:00:00+00:00",
                ),
                "b": self._entry(
                    "2024-01-01T12:00:00+00:00",
                    "2024-01-02T12:00:00+00:00",
                ),
            },
        )
        store = ScheduleStore(path=path)
        assert set(store._entries) == {"a", "b"}
        assert store.get("a").next_run == datetime(
            2024, 1, 2, 12, 0, tzinfo=timezone.utc
        )

    def test_one_unparseable_entry_does_not_wipe_valid_siblings(self, tmp_path):
        """Guard input: one bad entry is skipped, valid siblings survive."""
        path = str(tmp_path / "schedules.json")
        self._write(
            path,
            {
                "good": self._entry(
                    "2024-01-01T12:00:00+00:00",
                    "2024-01-02T12:00:00+00:00",
                ),
                "bad": self._entry(
                    "not-a-timestamp",
                    "not-a-timestamp",
                ),
            },
        )
        store = ScheduleStore(path=path)
        # The valid "good" entry must survive; only "bad" is dropped.
        assert "good" in store._entries
        assert store.get("good") is not None
        assert store.get("good").next_run == datetime(
            2024, 1, 2, 12, 0, tzinfo=timezone.utc
        )
        assert "bad" not in store._entries
