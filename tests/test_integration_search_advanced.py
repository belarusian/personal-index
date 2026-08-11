"""Advanced search integration tests for personal-index.

Tests multi-term search, fuzzy matching, pagination, and
search result quality after full pipeline processing.
"""

from __future__ import annotations

import os

import pytest

from personal_index.config.pipeline_config import PipelineConfig
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import Interest
from personal_index.pipeline_runner import PipelineRunner


class TestMultiTermSearch:
    """Test search with multiple query terms."""

    def test_multi_term_search(self, tmp_path):
        """Search with multiple terms should find matching pages."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "ml.txt").write_text(
            "Machine learning algorithms for natural language processing. "
            "Deep learning models achieve state-of-the-art results."
        )
        (docs / "web.txt").write_text(
            "Web development frameworks like Django and Flask. "
            "Building REST APIs and web applications."
        )

        runner = PipelineRunner(data_dir=data_dir)
        runner.run_from_files([
            str(docs / "ml.txt"),
            str(docs / "web.txt"),
        ])
        runner.close()

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))

        # Multi-term search
        results = index.search("machine learning")
        assert len(results) > 0

        results = index.search("web development")
        assert len(results) > 0

    def test_search_term_ranking(self, tmp_path):
        """Pages with more query term matches should rank higher."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        # Page with many "python" mentions
        (docs / "heavy.txt").write_text(
            "Python Python Python. Python is great. Python programming. "
            "Python libraries. Python frameworks. Python ecosystem."
        )
        # Page with few "python" mentions
        (docs / "light.txt").write_text(
            "Some text about other topics. Python is mentioned once."
        )

        runner = PipelineRunner(data_dir=data_dir)
        runner.run_from_files([
            str(docs / "heavy.txt"),
            str(docs / "light.txt"),
        ])
        runner.close()

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("python")
        assert len(results) >= 2
        # Heavy page should rank higher
        assert results[0].relevance_score > results[1].relevance_score


class TestSearchEdgeCases:
    """Test search edge cases and error handling."""

    def test_search_empty_query(self, tmp_path):
        """Empty query should return no results."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "test.txt").write_text("Some content here.")

        runner = PipelineRunner(data_dir=data_dir)
        runner.run_from_files([str(docs / "test.txt")])
        runner.close()

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("")
        assert len(results) == 0

    def test_search_special_characters(self, tmp_path):
        """Search with special characters should handle gracefully."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "test.txt").write_text(
            "Testing special characters: @#$%^&*() in content."
        )

        runner = PipelineRunner(data_dir=data_dir)
        runner.run_from_files([str(docs / "test.txt")])
        runner.close()

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        # Should not crash
        results = index.search("special @#$%")
        assert isinstance(results, list)

    def test_search_unicode_content(self, tmp_path):
        """Search should handle unicode content."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "unicode.txt").write_text(
            "Unicode content: café, naïve, résumé. "
            "International characters work correctly."
        )

        runner = PipelineRunner(data_dir=data_dir)
        runner.run_from_files([str(docs / "unicode.txt")])
        runner.close()

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("unicode")
        assert len(results) > 0

    def test_search_limit(self, tmp_path):
        """Search should respect result limit."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        for i in range(10):
            (docs / f"page{i}.txt").write_text(
                f"Page {i} about testing and software quality."
            )

        runner = PipelineRunner(data_dir=data_dir)
        runner.run_from_files([
            str(docs / f"page{i}.txt") for i in range(10)
        ])
        runner.close()

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("testing", limit=3)
        assert len(results) <= 3


class TestIndexOperations:
    """Test index CRUD operations."""

    def test_index_add_and_remove(self, tmp_path):
        """Pages should be addable and removable from index."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "test.txt").write_text("Test content for indexing.")

        runner = PipelineRunner(data_dir=data_dir)
        runner.run_from_files([str(docs / "test.txt")])
        runner.close()

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        assert index.get_page_count() >= 1

        # Get URL of indexed page
        pages = index.list_pages()
        url = pages[0].url

        # Remove page
        assert index.remove_page(url) is True
        assert index.get_page_count() == 0

    def test_index_clear(self, tmp_path):
        """Index clear should remove all pages."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        for i in range(5):
            (docs / f"page{i}.txt").write_text(f"Content for page {i}.")

        runner = PipelineRunner(data_dir=data_dir)
        runner.run_from_files([
            str(docs / f"page{i}.txt") for i in range(5)
        ])
        runner.close()

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        assert index.get_page_count() >= 5

        index.clear()
        assert index.get_page_count() == 0

    def test_index_get_page(self, tmp_path):
        """get_page should return page by URL."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "test.txt").write_text("Content to retrieve.")

        runner = PipelineRunner(data_dir=data_dir)
        runner.run_from_files([str(docs / "test.txt")])
        runner.close()

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        pages = index.list_pages()
        assert len(pages) > 0

        page = index.get_page(pages[0].url)
        assert page is not None
        assert page.url == pages[0].url

    def test_index_list_pages_sorted_by_score(self, tmp_path):
        """list_pages should return pages sorted by score descending."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        interest_store = InterestStore(
            store_path=os.path.join(data_dir, "interests.json")
        )
        interest_store.add(Interest(
            name="python", keywords=["python"]
        ))

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "high.txt").write_text("Python Python Python programming.")
        (docs / "low.txt").write_text("Unrelated content about weather.")

        runner = PipelineRunner(data_dir=data_dir)
        runner.run_from_files([
            str(docs / "high.txt"),
            str(docs / "low.txt"),
        ])
        runner.close()

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        pages = index.list_pages()
        assert len(pages) >= 2
        # Pages should be sorted by score descending
        for i in range(len(pages) - 1):
            assert pages[i].score >= pages[i + 1].score
