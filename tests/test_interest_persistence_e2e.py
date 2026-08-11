"""End-to-end tests for interest store persistence."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from personal_index.interests import InterestStore
from personal_index.models import Interest


class TestInterestPersistenceE2E:
    """Test interest store persistence with realistic scenarios."""

    def test_save_and_load(self, tmp_path):
        """Save interests and load them back."""
        path = str(tmp_path / "interests.json")
        store1 = InterestStore(store_path=path)
        
        # Add some interests
        store1.add(Interest(name="python", keywords=["python", "programming"]))
        store1.add(Interest(name="rust", keywords=["rust", "systems"]))
        
        # Verify saved
        assert os.path.exists(path)
        
        # Load new instance
        store2 = InterestStore(store_path=path)
        interests = store2.list_all()
        
        assert len(interests) == 2
        names = {i.name for i in interests}
        assert "python" in names
        assert "rust" in names

    def test_persistence_across_processes(self, tmp_path):
        """Interests persist across different process instances."""
        path = str(tmp_path / "interests.json")
        
        # First "process"
        store1 = InterestStore(store_path=path)
        store1.add(Interest(name="test", keywords=["test"]))
        del store1
        
        # Second "process" - simulate by creating new instance
        store2 = InterestStore(store_path=path)
        interests = store2.list_all()
        
        assert len(interests) == 1
        assert interests[0].name == "test"

    def test_persistence_with_complex_interests(self, tmp_path):
        """Complex interest objects persist correctly."""
        path = str(tmp_path / "interests.json")
        store = InterestStore(store_path=path)
        
        # Add interest with all fields
        interest = Interest(
            name="full_stack",
            keywords=["frontend", "backend", "api"],
            url_patterns=["*.example.com"],
            topics=["web", "development"],
            priority=8,
            enabled=True,
        )
        store.add(interest)
        
        # Load and verify
        store2 = InterestStore(store_path=path)
        loaded = store2.get("full_stack")
        
        assert loaded is not None
        assert loaded.name == "full_stack"
        assert "frontend" in loaded.keywords
        assert "web" in loaded.topics
        assert loaded.priority == 8

    def test_persistence_with_toggle(self, tmp_path):
        """Toggle state persists."""
        path = str(tmp_path / "interests.json")
        
        store1 = InterestStore(store_path=path)
        store1.add(Interest(name="test", keywords=["test"], enabled=True))
        store1.toggle("test")
        
        # Verify toggle persisted
        store2 = InterestStore(store_path=path)
        interest = store2.get("test")
        assert interest.enabled is False

    def test_persistence_with_remove(self, tmp_path):
        """Removed interests don't persist."""
        path = str(tmp_path / "interests.json")
        
        store1 = InterestStore(store_path=path)
        store1.add(Interest(name="keep", keywords=["keep"]))
        store1.add(Interest(name="remove", keywords=["remove"]))
        store1.remove("remove")
        
        # Verify remove persisted
        store2 = InterestStore(store_path=path)
        interests = store2.list_all()
        
        assert len(interests) == 1
        assert interests[0].name == "keep"

    def test_persistence_with_update(self, tmp_path):
        """Updated interests persist."""
        path = str(tmp_path / "interests.json")
        
        store1 = InterestStore(store_path=path)
        store1.add(Interest(name="test", keywords=["old"]))
        # Update by removing and re-adding
        store1.remove("test")
        store1.add(Interest(name="test", keywords=["new"]))
        
        # Verify update persisted
        store2 = InterestStore(store_path=path)
        interest = store2.get("test")
        
        assert interest is not None
        assert "new" in interest.keywords
        assert "old" not in interest.keywords

    def test_empty_file_handling(self, tmp_path):
        """Handle empty or corrupted file gracefully."""
        path = str(tmp_path / "interests.json")
        
        # Create empty file
        with open(path, "w") as f:
            f.write("")
        
        store = InterestStore(store_path=path)
        assert store.list_all() == []

    def test_invalid_json_handling(self, tmp_path):
        """Handle invalid JSON gracefully."""
        path = str(tmp_path / "interests.json")
        
        # Create invalid JSON file
        with open(path, "w") as f:
            f.write("{invalid json}")
        
        store = InterestStore(store_path=path)
        assert store.list_all() == []

    def test_large_number_of_interests(self, tmp_path):
        """Handle many interests."""
        path = str(tmp_path / "interests.json")
        store = InterestStore(store_path=path)
        
        # Add 100 interests
        for i in range(100):
            store.add(Interest(name=f"interest_{i}", keywords=[f"keyword_{i}"]))
        
        # Verify all persisted
        store2 = InterestStore(store_path=path)
        interests = store2.list_all()
        
        assert len(interests) == 100

    def test_interleaved_operations(self, tmp_path):
        """Multiple operations on same file."""
        path = str(tmp_path / "interests.json")
        
        store1 = InterestStore(store_path=path)
        store1.add(Interest(name="a", keywords=["a"]))
        
        store2 = InterestStore(store_path=path)
        store2.add(Interest(name="b", keywords=["b"]))
        
        store3 = InterestStore(store_path=path)
        interests = store3.list_all()
        
        assert len(interests) == 2
        names = {i.name for i in interests}
        assert "a" in names
        assert "b" in names
