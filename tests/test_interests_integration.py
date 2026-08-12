"""Integration tests for interest management across the pipeline."""

from __future__ import annotations

from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest, MatchMode


class TestInterestStoreIntegration:
    """Test interest store integration with filtering and scoring."""

    def test_add_and_retrieve_interest(self, tmp_path):
        """Test adding and retrieving an interest."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        interest = Interest(name="python", keywords=["python", "django"])
        store.add(interest)
        retrieved = store.get("python")
        assert retrieved is not None
        assert retrieved.keywords == ["python", "django"]

    def test_list_all_interests(self, tmp_path):
        """Test listing all interests."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"]))
        store.add(Interest(name="javascript", keywords=["javascript", "react"]))
        interests = store.list_all()
        assert len(interests) == 2

    def test_remove_interest(self, tmp_path):
        """Test removing an interest."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="temp", keywords=["temp"]))
        assert store.remove("temp") is True
        assert store.get("temp") is None

    def test_persistence_across_instances(self, tmp_path):
        """Test interests persist across store instances."""
        path = str(tmp_path / "interests.json")
        store1 = InterestStore(store_path=path)
        store1.add(Interest(name="python", keywords=["python", "django"]))

        store2 = InterestStore(store_path=path)
        interest = store2.get("python")
        assert interest is not None
        assert "python" in interest.keywords

    def test_matches_any_text(self, tmp_path):
        """Test matches_any with text content."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python", "django"]))
        store.add(Interest(name="web", keywords=["html", "css"]))

        matches = store.matches_any("This article is about python and django", "")
        assert len(matches) == 1
        assert matches[0].name == "python"

    def test_matches_any_url(self, tmp_path):
        """Test matches_any with URL patterns."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(
            name="github",
            keywords=["github"],
            url_patterns=["*github*"],
        ))

        matches = store.matches_any("", "https://github.com/user/repo")
        assert len(matches) == 1

    def test_total_score(self, tmp_path):
        """Test total score calculation."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"], priority=5))

        score = store.total_score("python python python")
        assert score > 0

    def test_get_all_keywords(self, tmp_path):
        """Test getting all keywords from all interests."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python", "django"]))
        store.add(Interest(name="web", keywords=["html", "css"]))

        keywords = store.get_all_keywords()
        assert "python" in keywords
        assert "django" in keywords
        assert "html" in keywords
        assert "css" in keywords

    def test_toggle_interest(self, tmp_path):
        """Test toggling interest enabled status."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"], enabled=True))

        toggled = store.toggle("python")
        assert toggled is not None
        assert toggled.enabled is False

        toggled = store.toggle("python")
        assert toggled.enabled is True

    def test_update_priority(self, tmp_path):
        """Test updating interest priority."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"], priority=5))

        updated = store.update_priority("python", 8)
        assert updated is not None
        assert updated.priority == 8

    def test_get_enabled_only(self, tmp_path):
        """Test getting only enabled interests."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="enabled", keywords=["test"], enabled=True))
        store.add(Interest(name="disabled", keywords=["test"], enabled=False))

        enabled = store.get_enabled()
        assert len(enabled) == 1
        assert enabled[0].name == "enabled"

    def test_interest_with_match_mode(self, tmp_path):
        """Test interest with different match modes."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(
            name="any_mode",
            keywords=["python", "javascript"],
            match_mode=MatchMode.ANY,
        ))

        # Should match with just one keyword
        matches = store.matches_any("This is about python", "")
        assert len(matches) == 1

    def test_interest_serialization(self, tmp_path):
        """Test interest serialization and deserialization."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        original = Interest(
            name="test",
            keywords=["python", "django"],
            priority=7,
            enabled=True,
        )
        store.add(original)

        # Reload from file
        store2 = InterestStore(store_path=str(tmp_path / "interests.json"))
        loaded = store2.get("test")
        assert loaded.name == "test"
        assert loaded.keywords == ["python", "django"]
        assert loaded.priority == 7
        assert loaded.enabled is True


class TestInterestFilteringIntegration:
    """Test interests integration with content filtering."""

    def test_interest_affects_filter(self, tmp_path):
        """Test that interests affect content filtering."""
        from personal_index.content_filter import ContentFilter, FilterConfig

        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python", "django"]))

        filter_cfg = FilterConfig(min_content_length=10, require_interest_match=True)
        content_filter = ContentFilter(config=filter_cfg, interest_store=store)

        matching_page = CrawledPage(
            url="https://example.com/python",
            title="Python Tutorial",
            content="This article is about python programming and django framework.",
        )
        assert content_filter.should_include(matching_page) is True

        non_matching_page = CrawledPage(
            url="https://example.com/cooking",
            title="Cooking Recipe",
            content="This recipe is about baking bread and making pasta.",
        )
        assert content_filter.should_include(non_matching_page) is False

    def test_interest_updates_affect_filter(self, tmp_path):
        """Test that updating interests affects filtering."""
        from personal_index.content_filter import ContentFilter, FilterConfig

        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"]))

        filter_cfg = FilterConfig(min_content_length=10, require_interest_match=True)
        content_filter = ContentFilter(config=filter_cfg, interest_store=store)

        page = CrawledPage(
            url="https://example.com/page",
            title="Page",
            content="This is about javascript programming.",
        )
        # Should not match python interest
        assert content_filter.should_include(page) is False

        # Add javascript to interest
        store.get("python").keywords.append("javascript")
        store._save()

        # Now should match
        assert content_filter.should_include(page) is True
