"""Search integration tests.

These tests verify search functionality works correctly with the full
pipeline, including indexing, scoring, and result formatting.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from personal_index.config.pipeline_config import PipelineConfig
from personal_index.index import SearchIndex
from personal_index.models import CrawledPage, Interest
from personal_index.pipeline_runner import PipelineRunner
from personal_index.tags import TagStore


class TestSearchIntegration:
    """Test search after full pipeline processing."""

    def _run_pipeline(self, tmp_path, pages):
        """Helper to run pipeline with given pages."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="programming",
            keywords=["python", "javascript", "programming", "language"],
        ))
        runner._interest_store.add(Interest(
            name="webdev",
            keywords=["web", "development", "frontend", "backend"],
        ))

        with patch.object(runner._crawler, "crawl", return_value=pages):
            with patch.object(runner._crawler, "close"):
                runner.run(["https://example.com"], max_depth=1)
        runner.close()
        return data_dir

    def test_search_returns_relevant_results(self, tmp_path):
        """Search returns pages matching query terms."""
        pages = [
            CrawledPage(
                url="https://example.com/python",
                title="Python Programming",
                content="Python is a great programming language for web development.",
            ),
            CrawledPage(
                url="https://example.com/cooking",
                title="Cooking Recipes",
                content="Delicious cooking recipes for home chefs.",
            ),
        ]
        data_dir = self._run_pipeline(tmp_path, pages)

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("python")
        assert len(results) == 1
        assert results[0].title == "Python Programming"
        index.close()

    def test_search_ranks_by_relevance(self, tmp_path):
        """Search ranks results by relevance score."""
        pages = [
            CrawledPage(
                url="https://example.com/python-heavy",
                title="Python Python Python",
                content="Python Python Python Python Python Python.",
            ),
            CrawledPage(
                url="https://example.com/python-light",
                title="Brief Python Mention",
                content="Python is mentioned once in this article.",
            ),
        ]
        data_dir = self._run_pipeline(tmp_path, pages)

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("python")
        assert len(results) == 2
        # Higher frequency should rank higher
        assert results[0].url == "https://example.com/python-heavy"
        index.close()

    def test_search_multi_term_query(self, tmp_path):
        """Search handles multi-term queries."""
        pages = [
            CrawledPage(
                url="https://example.com/python-web",
                title="Python Web Development",
                content="Python web development with Django and Flask frameworks.",
            ),
            CrawledPage(
                url="https://example.com/python-data",
                title="Python Data Science",
                content="Python data science with pandas and numpy libraries.",
            ),
        ]
        data_dir = self._run_pipeline(tmp_path, pages)

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("python web")
        assert len(results) >= 1
        # Python web page should rank highest for "python web" query
        assert results[0].url == "https://example.com/python-web"
        index.close()

    def test_search_case_insensitive(self, tmp_path):
        """Search is case-insensitive."""
        pages = [
            CrawledPage(
                url="https://example.com/python",
                title="Python Tutorial",
                content="Learn Python programming.",
            ),
        ]
        data_dir = self._run_pipeline(tmp_path, pages)

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        for query in ["python", "Python", "PYTHON", "PyThOn"]:
            results = index.search(query)
            assert len(results) == 1, f"Query '{query}' should find 1 result"
        index.close()

    def test_search_snippet_generation(self, tmp_path):
        """Search generates relevant snippets."""
        pages = [
            CrawledPage(
                url="https://example.com/long",
                title="Long Article",
                content="This is a very long article about many topics. "
                        "It discusses python programming in the middle section. "
                        "And continues with more content about other subjects.",
            ),
        ]
        data_dir = self._run_pipeline(tmp_path, pages)

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("python")
        assert len(results) == 1
        assert results[0].snippet is not None
        assert len(results[0].snippet) > 0
        assert "python" in results[0].snippet.lower()
        index.close()

    def test_search_with_tag_filter(self, tmp_path):
        """Search can be filtered by tags."""
        pages = [
            CrawledPage(
                url="https://example.com/python",
                title="Python Guide",
                content="Python programming guide for beginners.",
            ),
            CrawledPage(
                url="https://example.com/rust",
                title="Rust Guide",
                content="Rust programming guide for systems developers.",
            ),
        ]
        data_dir = self._run_pipeline(tmp_path, pages)

        # Tag only the python page
        tag_store = TagStore(store_path=os.path.join(data_dir, "tags.json"))
        tag_store.create_tag("important", color="#ff0000")
        tag_store.add_tag_to_page("https://example.com/python", "important")

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("programming")
        assert len(results) == 2

        # Filter by tag
        tagged_urls = tag_store.get_pages_for_tag("important")
        filtered = [r for r in results if r.url in tagged_urls]
        assert len(filtered) == 1
        assert filtered[0].url == "https://example.com/python"
        index.close()

    def test_search_empty_index(self, tmp_path):
        """Search handles empty index gracefully."""
        data_dir = str(tmp_path / "data")
        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("anything")
        assert results == []
        index.close()

    def test_search_limit_respected(self, tmp_path):
        """Search respects the limit parameter."""
        pages = [
            CrawledPage(
                url=f"https://example.com/page{i}",
                title=f"Python Page {i}",
                content=f"Python programming content for page {i}.",
            )
            for i in range(10)
        ]
        data_dir = self._run_pipeline(tmp_path, pages)

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("python", limit=3)
        assert len(results) == 3
        index.close()

    def test_search_result_has_all_fields(self, tmp_path):
        """Search results contain all expected fields."""
        pages = [
            CrawledPage(
                url="https://example.com/test",
                title="Test Page",
                content="Test content for search.",
            ),
        ]
        data_dir = self._run_pipeline(tmp_path, pages)

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("test")
        assert len(results) == 1
        result = results[0]
        assert result.url == "https://example.com/test"
        assert result.title == "Test Page"
        assert result.snippet is not None
        assert result.relevance_score > 0
        index.close()


class TestSearchIndexPersistence:
    """Test search index persistence and recovery."""

    def test_index_survives_restart(self, tmp_path):
        """Index data persists after closing and reopening."""
        data_dir = str(tmp_path / "data")
        db_path = os.path.join(data_dir, "search_index.json")

        # Create and populate
        index1 = SearchIndex(db_path=db_path)
        index1.add_page(CrawledPage(
            url="https://example.com/p1",
            title="Page One",
            content="First page content about programming.",
        ))
        index1.close()

        # Reopen and verify
        index2 = SearchIndex(db_path=db_path)
        assert index2.get_page_count() == 1
        results = index2.search("programming")
        assert len(results) == 1
        index2.close()

    def test_index_incremental_updates(self, tmp_path):
        """Index supports incremental updates."""
        data_dir = str(tmp_path / "data")
        db_path = os.path.join(data_dir, "search_index.json")

        index = SearchIndex(db_path=db_path)
        index.add_page(CrawledPage(
            url="https://example.com/p1",
            title="Page One",
            content="First page.",
        ))
        assert index.get_page_count() == 1

        index.add_page(CrawledPage(
            url="https://example.com/p2",
            title="Page Two",
            content="Second page.",
        ))
        assert index.get_page_count() == 2

        index.add_page(CrawledPage(
            url="https://example.com/p3",
            title="Page Three",
            content="Third page.",
        ))
        assert index.get_page_count() == 3
        index.close()

    def test_index_remove_page(self, tmp_path):
        """Index supports removing pages."""
        data_dir = str(tmp_path / "data")
        db_path = os.path.join(data_dir, "search_index.json")

        index = SearchIndex(db_path=db_path)
        index.add_page(CrawledPage(
            url="https://example.com/p1",
            title="Page One",
            content="First page.",
        ))
        index.add_page(CrawledPage(
            url="https://example.com/p2",
            title="Page Two",
            content="Second page.",
        ))
        assert index.get_page_count() == 2

        index.remove_page("https://example.com/p1")
        assert index.get_page_count() == 1
        results = index.search("first")
        assert len(results) == 0
        index.close()

    def test_index_clear(self, tmp_path):
        """Index supports clearing all data."""
        data_dir = str(tmp_path / "data")
        db_path = os.path.join(data_dir, "search_index.json")

        index = SearchIndex(db_path=db_path)
        index.add_page(CrawledPage(
            url="https://example.com/p1",
            title="Page One",
            content="First page.",
        ))
        assert index.get_page_count() == 1

        index.clear()
        assert index.get_page_count() == 0
        assert index.search("anything") == []
        index.close()
