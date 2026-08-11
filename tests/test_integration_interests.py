"""Integration tests for interest management."""

from __future__ import annotations

import os
import tempfile

import pytest

from personal_index.app import PersonalIndexApp
from personal_index.models import Interest


class TestInterestsIntegration:
    """Test interest management end-to-end."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.app = PersonalIndexApp(
            config_path=os.path.join(self.tmpdir, "config.yaml"),
            data_dir=os.path.join(self.tmpdir, "data"),
        )
        self.app.initialize()

    def test_add_single_interest(self):
        """Adding a single interest should work."""
        self.app.add_interest(name="Python", keywords=["python"], priority=8)
        interests = self.app.interest_store.list_all()
        assert len(interests) == 1
        assert interests[0].name == "Python"

    def test_add_multiple_interests(self):
        """Adding multiple interests should accumulate."""
        self.app.add_interest(name="Python", keywords=["python"])
        self.app.add_interest(name="AI", keywords=["ai", "ml"])
        self.app.add_interest(name="Web", keywords=["html", "css"])
        interests = self.app.interest_store.list_all()
        assert len(interests) == 3

    def test_interest_with_url_patterns(self):
        """Interests should support URL patterns."""
        self.app.add_interest(
            name="Tech News",
            keywords=["tech"],
            url_patterns=["https://techcrunch.com/*"],
        )
        interests = self.app.interest_store.list_all()
        assert len(interests) == 1
        assert "https://techcrunch.com/*" in interests[0].url_patterns

    def test_interest_persistence(self):
        """Interests should persist across store reloads."""
        self.app.add_interest(name="Test", keywords=["test"])
        # Reload store
        store_path = os.path.join(self.app.data_dir, "interests.json")
        from personal_index.interests import InterestStore
        new_store = InterestStore(store_path=store_path)
        interests = new_store.list_all()
        assert len(interests) >= 1
        assert any(i.name == "Test" for i in interests)

    def test_remove_interest(self):
        """Removing an interest should work."""
        self.app.add_interest(name="Temp", keywords=["temp"])
        assert len(self.app.interest_store.list_all()) == 1
        self.app.interest_store.remove("Temp")
        assert len(self.app.interest_store.list_all()) == 0

    def test_toggle_interest(self):
        """Toggling an interest should change its enabled state."""
        self.app.add_interest(name="ToggleTest", keywords=["toggle"])
        interests = self.app.interest_store.list_all()
        assert interests[0].enabled is True
        self.app.interest_store.toggle("ToggleTest")
        interests = self.app.interest_store.list_all()
        assert interests[0].enabled is False

    def test_interest_priority(self):
        """Interest priority should be stored correctly."""
        self.app.add_interest(name="High", keywords=["high"], priority=10)
        self.app.add_interest(name="Low", keywords=["low"], priority=1)
        interests = self.app.interest_store.list_all()
        priorities = {i.name: i.priority for i in interests}
        assert priorities["High"] == 10
        assert priorities["Low"] == 1

    def test_interest_matches_text(self):
        """Interest matching should work with keywords."""
        interest = Interest(name="Python", keywords=["python", "programming"])
        assert interest.matches("I love Python programming")
        assert interest.matches("Python is great")
        assert not interest.matches("I like apples")

    def test_interest_matches_url(self):
        """Interest matching should work with URL patterns."""
        interest = Interest(name="Tech", url_patterns=["https://techcrunch.com"])
        assert interest.matches("Tech news", url="https://techcrunch.com/article")

    def test_disabled_interest_does_not_match(self):
        """Disabled interests should not match."""
        interest = Interest(name="Disabled", keywords=["test"], enabled=False)
        assert not interest.matches("test content")
