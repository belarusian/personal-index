"""Tests for personal_index.interest_store."""

import json
import tempfile
from pathlib import Path

import pytest

from personal_index.interests import InterestStore
from personal_index.models import Interest, InterestType


@pytest.fixture
def store_path(tmp_path: Path) -> str:
    return str(tmp_path / "interests.json")


@pytest.fixture
def store(store_path: str) -> InterestStore:
    return InterestStore(store_path=store_path)


class TestInterestStore:
    """Tests for InterestStore."""

    def test_create_empty_store(self, store: InterestStore):
        assert store.list_all() == []

    def test_add_interest(self, store: InterestStore):
        interest = Interest(
            name="Python",
            interest_type=InterestType.KEYWORD,
            value="python",
            priority=7,
        )
        store.add(interest)
        all_interests = store.list_all()
        assert len(all_interests) == 1
        assert all_interests[0].name == "Python"

    def test_add_multiple_interests(self, store: InterestStore):
        store.add(Interest("Py", InterestType.KEYWORD, "python", 5))
        store.add(Interest("ML", InterestType.TOPIC, "machine learning", 8))
        assert len(store.list_all()) == 2

    def test_remove_interest(self, store: InterestStore):
        store.add(Interest("Py", InterestType.KEYWORD, "python", 5))
        assert store.remove("Py") is True
        assert len(store.list_all()) == 0

    def test_remove_nonexistent(self, store: InterestStore):
        assert store.remove("nonexistent") is False

    def test_get_interest(self, store: InterestStore):
        interest = Interest("Py", InterestType.KEYWORD, "python", 5)
        store.add(interest)
        found = store.get("Py")
        assert found is not None
        assert found.value == "python"

    def test_get_nonexistent(self, store: InterestStore):
        assert store.get("nonexistent") is None

    def test_list_enabled_only(self, store: InterestStore):
        store.add(Interest("A", InterestType.KEYWORD, "a", 5, enabled=True))
        store.add(Interest("B", InterestType.KEYWORD, "b", 5, enabled=False))
        assert len(store.get_enabled()) == 1
        assert len(store.list_all()) == 2

    def test_toggle_interest(self, store: InterestStore):
        store.add(Interest("A", InterestType.KEYWORD, "a", 5, enabled=True))
        toggled = store.toggle("A")
        assert toggled is not None
        assert toggled.enabled is False

    def test_toggle_nonexistent(self, store: InterestStore):
        assert store.toggle("nonexistent") is None

    def test_update_priority(self, store: InterestStore):
        store.add(Interest("A", InterestType.KEYWORD, "a", 5))
        updated = store.update_priority("A", 9)
        assert updated is not None
        assert updated.priority == 9

    def test_update_priority_clamped(self, store: InterestStore):
        store.add(Interest("A", InterestType.KEYWORD, "a", 5))
        store.update_priority("A", 15)
        assert store.get("A").priority == 10
        store.update_priority("A", -3)
        assert store.get("A").priority == 1

    def test_matches_any(self, store: InterestStore):
        store.add(Interest("Py", InterestType.KEYWORD, "python", 5))
        store.add(Interest("JS", InterestType.KEYWORD, "javascript", 5))
        matches = store.matches_any("I love python")
        assert len(matches) == 1
        assert matches[0].name == "Py"

    def test_total_score(self, store: InterestStore):
        store.add(Interest("Py", InterestType.KEYWORD, "python", 5))
        score = store.total_score("python python")
        assert score == 10.0

    def test_persistence(self, store_path: str):
        store1 = InterestStore(store_path=store_path)
        store1.add(Interest("Py", InterestType.KEYWORD, "python", 7))
        store2 = InterestStore(store_path=store_path)
        assert len(store2.list_all()) == 1
        assert store2.get("Py").priority == 7

    def test_load_corrupted_file(self, tmp_path: Path):
        path = str(tmp_path / "bad.json")
        Path(path).write_text("not json at all{{{")
        store = InterestStore(store_path=path)
        assert store.list_all() == []

    def test_creates_parent_dirs(self, tmp_path: Path):
        path = str(tmp_path / "nested" / "dir" / "interests.json")
        store = InterestStore(store_path=path)
        store.add(Interest("A", InterestType.KEYWORD, "a", 5))
        assert Path(path).exists()
