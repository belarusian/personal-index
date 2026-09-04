"""Tests for personal_index.interest_store."""

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
        store.add(Interest("Py", InterestType.KEYWORD, "python", priority=5))
        store.add(Interest("ML", InterestType.TOPIC, "machine learning", priority=8))
        assert len(store.list_all()) == 2

    def test_add_same_name_replaces_in_place(self, store: InterestStore):
        store.add(Interest("Py", InterestType.KEYWORD, "python", priority=5))
        store.add(Interest("Py", InterestType.KEYWORD, "python3", priority=9))
        assert len(store.list_all()) == 1
        updated = store.get("Py")
        assert updated is not None
        assert updated.value == "python3"
        assert updated.priority == 9

    def test_remove_interest(self, store: InterestStore):
        store.add(Interest("Py", InterestType.KEYWORD, "python", priority=5))
        assert store.remove("Py") is True
        assert len(store.list_all()) == 0

    def test_remove_nonexistent(self, store: InterestStore):
        assert store.remove("nonexistent") is False

    def test_get_interest(self, store: InterestStore):
        interest = Interest("Py", InterestType.KEYWORD, "python", priority=5)
        store.add(interest)
        found = store.get("Py")
        assert found is not None
        assert found.value == "python"

    def test_get_nonexistent(self, store: InterestStore):
        assert store.get("nonexistent") is None

    def test_list_enabled_only(self, store: InterestStore):
        store.add(Interest("A", InterestType.KEYWORD, "a", priority=5, enabled=True))
        store.add(Interest("B", InterestType.KEYWORD, "b", priority=5, enabled=False))
        assert len(store.get_enabled()) == 1
        assert len(store.list_all()) == 2

    def test_toggle_interest(self, store: InterestStore):
        store.add(Interest("A", InterestType.KEYWORD, "a", priority=5, enabled=True))
        toggled = store.toggle("A")
        assert toggled is not None
        assert toggled.enabled is False

    def test_toggle_nonexistent(self, store: InterestStore):
        assert store.toggle("nonexistent") is None

    def test_update_priority(self, store: InterestStore):
        store.add(Interest("A", InterestType.KEYWORD, "a", priority=5))
        updated = store.update_priority("A", 9)
        assert updated is not None
        assert updated.priority == 9

    def test_update_priority_clamped(self, store: InterestStore):
        store.add(Interest("A", InterestType.KEYWORD, "a", priority=5))
        store.update_priority("A", 15)
        a = store.get("A")
        assert a is not None
        assert a.priority == 10
        store.update_priority("A", -3)
        a = store.get("A")
        assert a is not None
        assert a.priority == 1

    def test_matches_any(self, store: InterestStore):
        store.add(Interest("Py", InterestType.KEYWORD, "python", priority=5))
        store.add(Interest("JS", InterestType.KEYWORD, "javascript", priority=5))
        matches = store.matches_any("I love python")
        assert len(matches) == 1
        assert matches[0].name == "Py"

    def test_total_score(self, store: InterestStore):
        store.add(Interest("Py", InterestType.KEYWORD, "python", priority=5))
        score = store.total_score("python python")
        assert score == 10.0

    def test_persistence(self, store_path: str):
        store1 = InterestStore(store_path=store_path)
        store1.add(Interest("Py", InterestType.KEYWORD, "python", priority=7))
        store2 = InterestStore(store_path=store_path)
        assert len(store2.list_all()) == 1
        py = store2.get("Py")
        assert py is not None
        assert py.priority == 7

    def test_load_corrupted_file(self, tmp_path: Path):
        path = str(tmp_path / "bad.json")
        Path(path).write_text("not json at all{{{")
        store = InterestStore(store_path=path)
        assert store.list_all() == []

    def test_creates_parent_dirs(self, tmp_path: Path):
        path = str(tmp_path / "nested" / "dir" / "interests.json")
        store = InterestStore(store_path=path)
        store.add(Interest("A", InterestType.KEYWORD, "a", priority=5))
        assert Path(path).exists()


def test_get_all_url_patterns_non_string_does_not_crash(tmp_path: Path):
    """TICKET-261: non-string url_patterns elements must not crash get_all_url_patterns()."""
    store = InterestStore(store_path=str(tmp_path / "interests.json"))
    store.add(Interest("A", InterestType.KEYWORD, "a", url_patterns=[1, "valid", None]))
    patterns = store.get_all_url_patterns()
    # Only the valid string pattern is compiled; non-string elements are skipped
    assert len(patterns) == 1
    assert patterns[0].pattern == "valid"
