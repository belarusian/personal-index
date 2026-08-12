"""Integration tests for interest management and scoring."""

from __future__ import annotations

from personal_index.interests import InterestStore
from personal_index.models import Interest


class TestInterestStore:
    """Test InterestStore CRUD operations."""

    def test_add_interest(self, tmp_path):
        """Test adding an interest."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))

        interest = Interest(
            name="python",
            keywords=["python", "django", "flask"],
            priority=8,
        )
        store.add(interest)

        retrieved = store.get("python")
        assert retrieved is not None
        assert "python" in retrieved.keywords

    def test_list_interests(self, tmp_path):
        """Test listing all interests."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))

        store.add(Interest(name="python", keywords=["python"]))
        store.add(Interest(name="javascript", keywords=["javascript"]))

        interests = store.list_all()
        assert len(interests) == 2
        names = {i.name for i in interests}
        assert "python" in names
        assert "javascript" in names

    def test_remove_interest(self, tmp_path):
        """Test removing an interest."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))

        store.add(Interest(name="test", keywords=["test"]))
        assert store.get("test") is not None

        result = store.remove("test")
        assert result is True
        assert store.get("test") is None

    def test_toggle_interest(self, tmp_path):
        """Test toggling interest enabled status."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))

        store.add(Interest(name="test", keywords=["test"], enabled=True))
        assert store.get("test").enabled is True

        result = store.toggle("test")
        assert result.enabled is False

    def test_get_enabled_interests(self, tmp_path):
        """Test getting only enabled interests."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))

        store.add(Interest(name="enabled", keywords=["a"], enabled=True))
        store.add(Interest(name="disabled", keywords=["b"], enabled=False))

        enabled = store.get_enabled()
        assert len(enabled) == 1
        assert enabled[0].name == "enabled"

    def test_update_priority(self, tmp_path):
        """Test updating interest priority."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))

        store.add(Interest(name="test", keywords=["test"], priority=5))
        result = store.update_priority("test", 8)
        assert result.priority == 8

    def test_get_all_keywords(self, tmp_path):
        """Test getting all keywords from interests."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))

        store.add(Interest(name="a", keywords=["python", "django"]))
        store.add(Interest(name="b", keywords=["javascript", "react"]))

        keywords = store.get_all_keywords()
        assert "python" in keywords
        assert "django" in keywords
        assert "javascript" in keywords
        assert "react" in keywords

    def test_matches_any(self, tmp_path):
        """Test matching text against interests."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))

        store.add(Interest(name="python", keywords=["python"]))
        store.add(Interest(name="js", keywords=["javascript"]))

        # Text matches python
        matches = store.matches_any("Python is great for programming")
        assert len(matches) == 1
        assert matches[0].name == "python"

        # Text matches both
        matches = store.matches_any(
            "Python and JavaScript are both popular programming languages"
        )
        assert len(matches) == 2

        # No match
        matches = store.matches_any("cooking recipes")
        assert len(matches) == 0

    def test_total_score(self, tmp_path):
        """Test calculating total relevance score."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))

        store.add(Interest(name="python", keywords=["python"], priority=8))
        store.add(Interest(name="web", keywords=["web"], priority=6))

        # Text matches python once
        score = store.total_score("Python programming")
        assert score > 0

        # Text matches both
        score2 = store.total_score("Python web development")
        assert score2 > score


class TestInterestScoring:
    """Test interest-based scoring."""

    def test_interest_matches_text(self, tmp_path):
        """Test Interest.matches() with text."""
        interest = Interest(
            name="python",
            keywords=["python", "django"],
            priority=8,
        )

        assert interest.matches("Python programming")
        assert interest.matches("Django web framework")
        assert not interest.matches("cooking recipes")

    def test_interest_matches_url(self, tmp_path):
        """Test Interest.matches() with URL patterns."""
        interest = Interest(
            name="docs",
            url_patterns=["example.com/docs/*"],
            priority=7,
        )

        assert interest.matches("content", "https://example.com/docs/page")
        assert not interest.matches("content", "https://example.com/other")

    def test_interest_priority_clamping(self, tmp_path):
        """Test that priority is clamped to 1-10."""
        # Priority too low
        interest = Interest(name="test", keywords=["a"], priority=0)
        assert interest.priority == 1

        # Priority too high
        interest = Interest(name="test2", keywords=["b"], priority=15)
        assert interest.priority == 10

        # Valid priority
        interest = Interest(name="test3", keywords=["c"], priority=5)
        assert interest.priority == 5

    def test_interest_score(self, tmp_path):
        """Test Interest.score() calculation."""
        interest = Interest(
            name="python",
            keywords=["python"],
            priority=10,
        )

        # No matches
        score = interest.score("cooking recipes")
        assert score == 0.0

        # One match
        score = interest.score("Python programming")
        assert score > 0

        # Multiple matches
        score = interest.score("Python Python Python")
        assert score > interest.score("Python")


class TestInterestPersistence:
    """Test InterestStore data persistence."""

    def test_save_and_reload(self, tmp_path):
        """Test interests persist to disk and can be reloaded."""
        path = str(tmp_path / "interests.json")

        # Create and save
        store1 = InterestStore(store_path=path)
        store1.add(Interest(name="test", keywords=["a"], priority=7))
        store1._save()

        # Reload
        store2 = InterestStore(store_path=path)
        interest = store2.get("test")
        assert interest is not None
        assert "a" in interest.keywords
        assert interest.priority == 7

    def test_clear_store(self, tmp_path):
        """Test clearing all interests."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))

        store.add(Interest(name="a", keywords=["1"]))
        store.add(Interest(name="b", keywords=["2"]))

        assert len(store.list_all()) == 2

        # Clear
        store._interests.clear()
        store._save()

        assert len(store.list_all()) == 0
