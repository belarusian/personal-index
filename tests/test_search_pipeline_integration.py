"""Integration tests for search within the full pipeline context.

Tests that search works correctly after content has been processed
through the full crawl→extract→filter→score→tag→index pipeline.
"""

from __future__ import annotations

from personal_index.models import CrawledPage, Interest
from personal_index.pipeline_runner import PipelineConfig, PipelineRunner


class TestSearchAfterPipeline:
    """Test search functionality after pipeline processing."""

    def test_search_finds_indexed_content(self, tmp_path):
        """Test that search finds content indexed by the pipeline."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(pipeline_config=cfg, data_dir=data_dir)

        runner._interest_store.add(Interest(
            name="python",
            keywords=["python", "programming"],
        ))

        page = CrawledPage(
            url="https://example.com/python-guide",
            title="Python Programming Guide",
            content="Python is a versatile programming language used for web development, "
                    "data science, machine learning, and automation. Python programming "
                    "is popular among beginners and experts alike.",
        )
        runner.add_page_directly(page)

        results = runner._search_index.search("python")
        assert len(results) == 1
        assert "Python" in results[0].title
        assert "python-guide" in results[0].url
        assert results[0].relevance_score > 0

    def test_search_multiple_pages_ranked_by_relevance(self, tmp_path):
        """Test that search ranks results by relevance."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(pipeline_config=cfg, data_dir=data_dir)

        runner._interest_store.add(Interest(
            name="tech",
            keywords=["python", "javascript"],
        ))

        # Page with many keyword matches
        page1 = CrawledPage(
            url="https://example.com/python-heavy",
            title="Python Python Python",
            content="Python programming in Python with Python libraries for Python development.",
        )
        # Page with few keyword matches
        page2 = CrawledPage(
            url="https://example.com/python-light",
            title="Brief Python Mention",
            content="Python is mentioned once in this article about other topics.",
        )
        runner.add_page_directly(page1)
        runner.add_page_directly(page2)

        results = runner._search_index.search("python")
        assert len(results) == 2
        # Page with more matches should rank higher
        assert results[0].url == "https://example.com/python-heavy"
        assert results[0].relevance_score > results[1].relevance_score

    def test_search_with_snippet(self, tmp_path):
        """Test that search results include relevant snippets."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(pipeline_config=cfg, data_dir=data_dir)

        runner._interest_store.add(Interest(
            name="web",
            keywords=["javascript", "web"],
        ))

        page = CrawledPage(
            url="https://example.com/js-guide",
            title="JavaScript Guide",
            content="JavaScript is the most popular programming language for web development. "
                    "It runs in browsers and on servers with Node.js.",
        )
        runner.add_page_directly(page)

        results = runner._search_index.search("javascript")
        assert len(results) == 1
        assert len(results[0].snippet) > 0
        assert "JavaScript" in results[0].snippet or "javascript" in results[0].snippet.lower()

    def test_search_empty_query(self, tmp_path):
        """Test search with empty query returns no results."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(pipeline_config=cfg, data_dir=data_dir)

        runner._interest_store.add(Interest(name="test", keywords=["test"]))
        page = CrawledPage(
            url="https://example.com/page",
            title="Test Page",
            content="This is a test page with some content.",
        )
        runner.add_page_directly(page)

        results = runner._search_index.search("")
        assert len(results) == 0

    def test_search_no_results(self, tmp_path):
        """Test search with no matching content."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(pipeline_config=cfg, data_dir=data_dir)

        runner._interest_store.add(Interest(name="python", keywords=["python"]))
        page = CrawledPage(
            url="https://example.com/rust",
            title="Rust Programming",
            content="Rust is a systems programming language focused on safety and performance.",
        )
        runner.add_page_directly(page)

        results = runner._search_index.search("python")
        assert len(results) == 0

    def test_search_limit_results(self, tmp_path):
        """Test that search respects the limit parameter."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(pipeline_config=cfg, data_dir=data_dir)

        runner._interest_store.add(Interest(name="tech", keywords=["programming"]))

        for i in range(10):
            page = CrawledPage(
                url=f"https://example.com/page{i}",
                title=f"Programming Page {i}",
                content=f"This is programming content page number {i}.",
            )
            runner.add_page_directly(page)

        results = runner._search_index.search("programming", limit=3)
        assert len(results) == 3

    def test_search_case_insensitive(self, tmp_path):
        """Test that search is case-insensitive."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(pipeline_config=cfg, data_dir=data_dir)

        runner._interest_store.add(Interest(name="python", keywords=["python"]))
        page = CrawledPage(
            url="https://example.com/page",
            title="Python Guide",
            content="Python programming language guide.",
        )
        runner.add_page_directly(page)

        for query in ["python", "Python", "PYTHON", "PyThOn"]:
            results = runner._search_index.search(query)
            assert len(results) == 1, f"Search failed for query: {query}"

    def test_search_with_stop_words(self, tmp_path):
        """Test that stop words are handled correctly in search."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(pipeline_config=cfg, data_dir=data_dir)

        runner._interest_store.add(Interest(name="python", keywords=["python"]))
        page = CrawledPage(
            url="https://example.com/page",
            title="Python Guide",
            content="Python is a great programming language for web development.",
        )
        runner.add_page_directly(page)

        # Search with stop words mixed in
        results = runner._search_index.search("the python programming")
        assert len(results) == 1


class TestSearchWithTags:
    """Test search integration with tag system."""

    def test_search_and_tags_coexist(self, tmp_path):
        """Test that search index and tag store work together."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(pipeline_config=cfg, data_dir=data_dir)

        runner._interest_store.add(Interest(name="python", keywords=["python"]))
        page = CrawledPage(
            url="https://example.com/blog/python-tips",
            title="Python Tips",
            content="Python programming tips and tricks for web development.",
        )
        runner.add_page_directly(page)

        # Verify both search and tags work
        search_results = runner._search_index.search("python")
        assert len(search_results) == 1

        page_tags = runner._tag_store.get_tags_for_page("https://example.com/blog/python-tips")
        tag_names = [t.name for t in page_tags]
        assert "python" in tag_names
        assert "programming" in tag_names

    def test_tags_persist_with_search_index(self, tmp_path):
        """Test that tags and search index persist together."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)

        # First runner: add content
        runner1 = PipelineRunner(pipeline_config=cfg, data_dir=data_dir)
        runner1._interest_store.add(Interest(name="python", keywords=["python"]))
        page = CrawledPage(
            url="https://example.com/page",
            title="Python Page",
            content="Python programming language for web development.",
        )
        runner1.add_page_directly(page)

        # Second runner: verify both persist
        runner2 = PipelineRunner(pipeline_config=cfg, data_dir=data_dir)
        search_results = runner2._search_index.search("python")
        assert len(search_results) == 1

        page_tags = runner2._tag_store.get_tags_for_page("https://example.com/page")
        tag_names = [t.name for t in page_tags]
        assert "python" in tag_names
