"""End-to-end tests for interest management."""

from __future__ import annotations

from personal_index.interests import InterestStore
from personal_index.models import Interest


class TestInterestStoreE2E:
    """Test interest store with realistic workflows."""

    def test_add_and_list_interests(self, tmp_path):
        """Add interests and verify they are listed."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python", "programming"]))
        store.add(Interest(name="rust", keywords=["rust", "systems"]))
        interests = store.list_all()
        assert len(interests) == 2
        names = {i.name for i in interests}
        assert "python" in names
        assert "rust" in names

    def test_remove_interest(self, tmp_path):
        """Remove an interest by name."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"]))
        store.add(Interest(name="rust", keywords=["rust"]))
        assert store.remove("python")
        interests = store.list_all()
        assert len(interests) == 1
        assert interests[0].name == "rust"

    def test_remove_nonexistent_interest(self, tmp_path):
        """Removing nonexistent interest returns False."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        assert not store.remove("nonexistent")

    def test_persistence_across_instances(self, tmp_path):
        """Interests persist across InterestStore instances."""
        path = str(tmp_path / "interests.json")
        store1 = InterestStore(store_path=path)
        store1.add(Interest(name="test", keywords=["test"]))
        del store1

        store2 = InterestStore(store_path=path)
        interests = store2.list_all()
        assert len(interests) == 1
        assert interests[0].name == "test"

    def test_toggle_interest(self, tmp_path):
        """Toggle interest enabled/disabled state."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"], enabled=True))
        store.toggle("python")
        interests = store.list_all()
        assert interests[0].enabled is False
        store.toggle("python")
        interests = store.list_all()
        assert interests[0].enabled is True

    def test_interest_matching(self, tmp_path):
        """Interest matches content by keywords."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python", "programming"]))
        interest = store.get("python")
        assert interest is not None
        assert interest.matches("Python is great for programming", "")
        assert not interest.matches("Rust is great for systems", "")

    def test_empty_store(self, tmp_path):
        """Empty store returns empty list."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        assert store.list_all() == []
        assert store.get("nonexistent") is None
