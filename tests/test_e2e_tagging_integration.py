"""Tagging integration tests.

These tests verify tag management, persistence, and integration with
the pipeline and search functionality.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from personal_index.config.pipeline_config import PipelineConfig
from personal_index.index import SearchIndex
from personal_index.models import CrawledPage, Interest
from personal_index.pipeline_runner import PipelineRunner
from personal_index.tags import TagStore


class TestTagStoreIntegration:
    """Test TagStore persistence and operations."""

    def test_tag_create_and_list(self, tmp_path):
        """Can create and list tags."""
        store = TagStore(store_path=str(tmp_path / "tags.json"))
        store.create_tag("python", color="#3572A5")
        store.create_tag("web", color="#2ecc71")
        store.create_tag("important", color="#e74c3c")

        tags = store.list_tags()
        assert len(tags) == 3
        names = {t.name for t in tags}
        assert names == {"python", "web", "important"}

    def test_tag_add_to_page(self, tmp_path):
        """Can add tags to pages."""
        store = TagStore(store_path=str(tmp_path / "tags.json"))
        store.create_tag("python", color="#3572A5")
        store.create_tag("tutorial", color="#9b59b6")

        store.add_tag_to_page("https://example.com/page1", "python")
        store.add_tag_to_page("https://example.com/page1", "tutorial")
        store.add_tag_to_page("https://example.com/page2", "python")

        # Page 1 should have both tags
        tags = store.get_tags_for_page("https://example.com/page1")
        tag_names = {t.name for t in tags}
        assert tag_names == {"python", "tutorial"}

        # Page 2 should have only python
        tags = store.get_tags_for_page("https://example.com/page2")
        tag_names = {t.name for t in tags}
        assert tag_names == {"python"}

    def test_tag_get_pages_for_tag(self, tmp_path):
        """Can get all pages for a tag."""
        store = TagStore(store_path=str(tmp_path / "tags.json"))
        store.create_tag("python", color="#3572A5")

        store.add_tag_to_page("https://example.com/p1", "python")
        store.add_tag_to_page("https://example.com/p2", "python")
        store.add_tag_to_page("https://example.com/p3", "python")
        store.add_tag_to_page("https://example.com/p4", "other")

        pages = store.get_pages_for_tag("python")
        assert len(pages) == 3
        assert "https://example.com/p1" in pages

    def test_tag_remove_from_page(self, tmp_path):
        """Can remove tags from pages."""
        store = TagStore(store_path=str(tmp_path / "tags.json"))
        store.create_tag("python", color="#3572A5")
        store.add_tag_to_page("https://example.com/p1", "python")

        assert len(store.get_tags_for_page("https://example.com/p1")) == 1
        store.remove_tag_from_page("https://example.com/p1", "python")
        assert len(store.get_tags_for_page("https://example.com/p1")) == 0

    def test_tag_delete(self, tmp_path):
        """Can delete tags."""
        store = TagStore(store_path=str(tmp_path / "tags.json"))
        store.create_tag("python", color="#3572A5")
        store.create_tag("web", color="#2ecc71")
        store.add_tag_to_page("https://example.com/p1", "python")

        assert store.get_tag_count() == 2
        store.delete_tag("python")
        assert store.get_tag_count() == 1

    def test_tag_persistence(self, tmp_path):
        """Tags persist to disk and reload."""
        path = str(tmp_path / "tags.json")
        store1 = TagStore(store_path=path)
        store1.create_tag("python", color="#3572A5")
        store1.add_tag_to_page("https://example.com/p1", "python")

        # Reload
        store2 = TagStore(store_path=path)
        tags = store2.list_tags()
        assert len(tags) == 1
        assert tags[0].name == "python"
        pages = store2.get_pages_for_tag("python")
        assert "https://example.com/p1" in pages

    def test_tag_count(self, tmp_path):
        """Tag count methods work correctly."""
        store = TagStore(store_path=str(tmp_path / "tags.json"))
        store.create_tag("python", color="#3572A5")
        store.create_tag("web", color="#2ecc71")
        store.add_tag_to_page("https://example.com/p1", "python")
        store.add_tag_to_page("https://example.com/p2", "python")
        store.add_tag_to_page("https://example.com/p2", "web")

        assert store.get_tag_count() == 2
        assert store.get_tagged_page_count() == 2

    def test_tag_clear(self, tmp_path):
        """Clear removes all tags."""
        store = TagStore(store_path=str(tmp_path / "tags.json"))
        store.create_tag("python", color="#3572A5")
        store.add_tag_to_page("https://example.com/p1", "python")

        store.clear()
        assert store.get_tag_count() == 0
        assert store.get_tagged_page_count() == 0


class TestTagPipelineIntegration:
    """Test tagging within the pipeline."""

    def test_pipeline_auto_creates_tags_from_interests(self, tmp_path):
        """Pipeline auto-creates tags from matched interests."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="python",
            keywords=["python", "django"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/python",
                title="Python Guide",
                content="Python Django programming.",
            ),
        ]

        with patch.object(runner._crawler, "crawl", return_value=pages), patch.object(runner._crawler, "close"):
            runner.run(["https://example.com"], max_depth=1)
        runner.close()

        # Verify tag was created
        tag_store = TagStore(store_path=os.path.join(data_dir, "tags.json"))
        tags = tag_store.list_tags()
        tag_names = {t.name for t in tags}
        assert "python" in tag_names

    def test_pipeline_tags_multiple_interests(self, tmp_path):
        """Pipeline tags pages matching multiple interests."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="python",
            keywords=["python"],
        ))
        runner._interest_store.add(Interest(
            name="webdev",
            keywords=["web", "development"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/python-web",
                title="Python Web Development",
                content="Python web development with Django.",
            ),
        ]

        with patch.object(runner._crawler, "crawl", return_value=pages), patch.object(runner._crawler, "close"):
            runner.run(["https://example.com"], max_depth=1)
        runner.close()

        tag_store = TagStore(store_path=os.path.join(data_dir, "tags.json"))
        tags = tag_store.get_tags_for_page("https://example.com/python-web")
        tag_names = {t.name for t in tags}
        assert "python" in tag_names
        assert "webdev" in tag_names

    def test_pipeline_unmatched_pages_not_tagged(self, tmp_path):
        """Pages not matching interests are not auto-tagged."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="python",
            keywords=["python"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/cooking",
                title="Cooking Guide",
                content="Recipes and cooking tips for home chefs.",
            ),
        ]

        with patch.object(runner._crawler, "crawl", return_value=pages), patch.object(runner._crawler, "close"):
            runner.run(["https://example.com"], max_depth=1)
        runner.close()

        tag_store = TagStore(store_path=os.path.join(data_dir, "tags.json"))
        tags = tag_store.get_tags_for_page("https://example.com/cooking")
        # Should not have python tag
        tag_names = {t.name for t in tags}
        assert "python" not in tag_names


class TestTagSearchIntegration:
    """Test tag-based search filtering."""

    def test_search_filtered_by_tag(self, tmp_path):
        """Search results can be filtered by tag."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(name="python", keywords=["python"]))
        runner._interest_store.add(Interest(name="webdev", keywords=["web"]))

        pages = [
            CrawledPage(
                url="https://example.com/python",
                title="Python Guide",
                content="Python programming for web development.",
            ),
            CrawledPage(
                url="https://example.com/rust",
                title="Rust Guide",
                content="Rust programming for systems development.",
            ),
        ]

        with patch.object(runner._crawler, "crawl", return_value=pages), patch.object(runner._crawler, "close"):
            runner.run(["https://example.com"], max_depth=1)
        runner.close()

        # Search and filter by tag
        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        tag_store = TagStore(store_path=os.path.join(data_dir, "tags.json"))

        results = index.search("programming")
        {r.url for r in results}

        # Filter by python tag
        python_pages = tag_store.get_pages_for_tag("python")
        python_results = [r for r in results if r.url in python_pages]
        assert len(python_results) >= 1
        assert any("python" in r.url for r in python_results)
        index.close()
