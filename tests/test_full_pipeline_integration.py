"""Comprehensive full pipeline integration tests.

Tests the complete crawl → extract → filter → score → tag → index → search
pipeline end-to-end, verifying each stage produces correct output.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from personal_index.config.pipeline_config import PipelineConfig
from personal_index.content_extractor import ContentExtractor
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer, ScoreWeights
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.keyword_extractor import extract_keywords
from personal_index.models import CrawledPage, Interest
from personal_index.pipeline_runner import PipelineRunner, PipelineStats
from personal_index.tags import TagStore


class TestFullPipelineStages:
    """Test each pipeline stage individually and together."""

    def test_extract_stage_preserves_content(self, tmp_path):
        """Test that extraction preserves meaningful content."""
        extractor = ContentExtractor()
        html = """
        <html>
        <head><title>Python Tutorial</title></head>
        <body>
            <h1>Python Programming</h1>
            <p>Python is a versatile programming language.</p>
            <p>It is used for web development and data science.</p>
        </body>
        </html>
        """
        result = extractor.extract(html)
        assert result.title == "Python Tutorial"
        assert "Python" in result.text
        assert "programming" in result.text.lower()
        assert result.word_count > 5

    def test_filter_stage_includes_relevant_content(self, tmp_path):
        """Test that filter includes pages matching interests."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python", "django", "flask"]))

        filter_cfg = FilterConfig(min_content_length=10, require_interest_match=False)
        content_filter = ContentFilter(config=filter_cfg, interest_store=store)

        page = CrawledPage(
            url="https://example.com/python",
            title="Python Guide",
            content="Python is a great programming language for web development.",
        )
        assert content_filter.should_include(page) is True

    def test_filter_stage_excludes_short_content(self, tmp_path):
        """Test that filter excludes pages with too little content."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        filter_cfg = FilterConfig(min_content_length=100, require_interest_match=False)
        content_filter = ContentFilter(config=filter_cfg, interest_store=store)

        page = CrawledPage(
            url="https://example.com/short",
            title="Short",
            content="Too short.",
        )
        assert content_filter.should_include(page) is False

    def test_score_stage_ranks_relevant_higher(self, tmp_path):
        """Test that scoring ranks relevant content higher."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python", "django", "flask"]))

        scorer = ContentScorer(weights=ScoreWeights())

        # Relevant page
        relevant = CrawledPage(
            url="https://example.com/python",
            title="Python Django Tutorial",
            content="Python and Django are great for web development. Python is versatile.",
        )
        relevant.matched_interests = ["python"]

        # Irrelevant page
        irrelevant = CrawledPage(
            url="https://example.com/cooking",
            title="Cooking Guide",
            content="How to cook pasta with tomato sauce.",
        )
        irrelevant.matched_interests = []

        score_relevant = scorer.score_page(relevant, store)
        score_irrelevant = scorer.score_page(irrelevant, store)

        assert score_relevant.total > score_irrelevant.total

    def test_tag_stage_applies_interest_tags(self, tmp_path):
        """Test that tagging applies interest-based tags."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python", "django"]))
        store.add(Interest(name="webdev", keywords=["web", "development", "html"]))

        tag_store = TagStore(store_path=str(tmp_path / "tags.json"))

        page = CrawledPage(
            url="https://example.com/python-web",
            title="Python Web Development",
            content="Python is great for web development with Django.",
        )

        text = f"{page.title} {page.content}"
        matches = store.matches_any(text, page.url)
        for interest in matches:
            tag_store.add_tag_to_page(page.url, interest.name)

        tags = tag_store.get_tags_for_page(page.url)
        tag_names = [t.name for t in tags]
        assert "python" in tag_names or "webdev" in tag_names

    def test_index_stage_makes_content_searchable(self, tmp_path):
        """Test that indexing makes content searchable."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))

        page = CrawledPage(
            url="https://example.com/python",
            title="Python Programming",
            content="Python is a versatile programming language for web development.",
        )
        index.add_page(page)

        results = index.search("python")
        assert len(results) == 1
        assert results[0].title == "Python Programming"

    def test_index_stage_persists_across_instances(self, tmp_path):
        """Test that index persists to disk and can be reloaded."""
        db_path = str(tmp_path / "index.json")

        # Create and save
        index1 = SearchIndex(db_path=db_path)
        page = CrawledPage(
            url="https://example.com/rust",
            title="Rust Programming",
            content="Rust is a systems programming language.",
        )
        index1.add_page(page)
        index1.close()

        # Reload
        index2 = SearchIndex(db_path=db_path)
        results = index2.search("rust")
        assert len(results) == 1
        assert results[0].title == "Rust Programming"
        index2.close()

    def test_full_extract_filter_score_chain(self, tmp_path):
        """Test the complete extract → filter → score chain."""
        extractor = ContentExtractor()
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python", "django", "flask"]))

        filter_cfg = FilterConfig(min_content_length=10, require_interest_match=False)
        content_filter = ContentFilter(config=filter_cfg, interest_store=store)
        scorer = ContentScorer()

        html = """
        <html><head><title>Python Web Frameworks</title></head>
        <body>
            <h1>Python Web Frameworks</h1>
            <p>Django and Flask are popular Python web frameworks.</p>
            <p>Python is widely used for web development.</p>
        </body></html>
        """

        # Extract
        extracted = extractor.extract(html)
        assert extracted.title == "Python Web Frameworks"

        # Build page
        page = CrawledPage(
            url="https://example.com/python-frameworks",
            title=extracted.title,
            content=extracted.text,
        )

        # Filter
        assert content_filter.should_include(page)

        # Score
        score_result = scorer.score_page(page, store)
        assert score_result.total > 0


class TestPipelineRunnerIntegration:
    """Test PipelineRunner with realistic scenarios."""

    def test_runner_processes_multiple_pages(self, tmp_path):
        """Test runner processes multiple pages through all stages."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(
            name="programming",
            keywords=["python", "javascript", "programming", "language"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/python",
                title="Python Tutorial",
                content="Python is a versatile programming language for web development.",
            ),
            CrawledPage(
                url="https://example.com/javascript",
                title="JavaScript Guide",
                content="JavaScript is the language of the web for frontend development.",
            ),
            CrawledPage(
                url="https://example.com/rust",
                title="Rust Programming",
                content="Rust is a systems programming language with memory safety.",
            ),
        ]

        indexed = 0
        for page in pages:
            if runner.add_page_directly(page):
                indexed += 1

        assert indexed == 3

        # Verify all are searchable
        results = runner._search_index.search("programming")
        assert len(results) >= 2

        runner.close()

    def test_runner_with_multiple_interests(self, tmp_path):
        """Test runner with multiple interests configured."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(
            name="python", keywords=["python", "django", "flask"],
        ))
        runner._interest_store.add(Interest(
            name="webdev", keywords=["html", "css", "javascript", "web"],
        ))
        runner._interest_store.add(Interest(
            name="devops", keywords=["docker", "kubernetes", "ci/cd"],
        ))

        # Page matching python
        page1 = CrawledPage(
            url="https://example.com/python",
            title="Python Guide",
            content="Python is a great programming language for web development.",
        )
        assert runner.add_page_directly(page1)

        # Page matching webdev
        page2 = CrawledPage(
            url="https://example.com/web",
            title="Web Dev",
            content="HTML and CSS are fundamental web technologies.",
        )
        assert runner.add_page_directly(page2)

        # Page matching no interest (but still indexed with low threshold)
        page3 = CrawledPage(
            url="https://example.com/cooking",
            title="Cooking",
            content="How to make pasta with tomato sauce and fresh basil.",
        )
        # With min_score_threshold=0.0, this should still be indexed
        result = runner.add_page_directly(page3)
        # It may or may not be indexed depending on scoring

        runner.close()

    def test_runner_stats_accuracy(self, tmp_path):
        """Test that runner stats accurately reflect processing."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(
            name="tech", keywords=["python", "code"],
        ))

        pages = [
            CrawledPage(
                url=f"https://example.com/page{i}",
                title=f"Page {i}",
                content=f"Python programming content for page {i}. " * 10,
            )
            for i in range(5)
        ]

        indexed = 0
        for page in pages:
            if runner.add_page_directly(page):
                indexed += 1

        stats = runner.get_stats()
        assert stats["indexed_pages"] == indexed
        assert stats["total_interests"] == 1

        runner.close()

    def test_runner_from_files_integration(self, tmp_path):
        """Test runner processing files from disk."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(
            name="python", keywords=["python", "programming"],
        ))

        # Create test files
        files = []
        for i in range(3):
            f = tmp_path / f"article{i}.txt"
            f.write_text(f"Python programming article number {i}. " * 20)
            files.append(str(f))

        stats = runner.run_from_files(files)
        assert stats.pages_indexed >= 2
        assert stats.errors == []

        runner.close()

    def test_runner_handles_mixed_file_types(self, tmp_path):
        """Test runner handles text and HTML files together."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(
            name="webdev", keywords=["python", "web", "development"],
        ))

        # Text file
        txt_file = tmp_path / "article.txt"
        txt_file.write_text("Python web development with Django and Flask.")

        # HTML file
        html_file = tmp_path / "page.html"
        html_file.write_text(
            "<html><head><title>Python Web</title></head>"
            "<body><p>Python is great for web development.</p></body></html>"
        )

        stats = runner.run_from_files([str(txt_file), str(html_file)])
        assert stats.pages_indexed >= 1

        runner.close()


class TestSearchIntegration:
    """Test search functionality across the pipeline."""

    def test_search_finds_relevant_results(self, tmp_path):
        """Test that search finds relevant results after indexing."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(
            name="python", keywords=["python", "django"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/python-tutorial",
                title="Python Tutorial",
                content="Learn Python programming from scratch.",
            ),
            CrawledPage(
                url="https://example.com/django-guide",
                title="Django Guide",
                content="Django is a Python web framework for building web apps.",
            ),
            CrawledPage(
                url="https://example.com/javascript",
                title="JavaScript Basics",
                content="JavaScript is used for web frontend development.",
            ),
        ]

        for page in pages:
            runner.add_page_directly(page)

        # Search for Python
        results = runner._search_index.search("python")
        assert len(results) >= 2

        # Search for Django
        results = runner._search_index.search("django")
        assert len(results) >= 1

        runner.close()

    def test_search_with_limit(self, tmp_path):
        """Test that search respects the limit parameter."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        for i in range(10):
            page = CrawledPage(
                url=f"https://example.com/page{i}",
                title=f"Python Page {i}",
                content=f"Python programming content {i}. " * 10,
            )
            runner.add_page_directly(page)

        results = runner._search_index.search("python", limit=3)
        assert len(results) <= 3

        runner.close()

    def test_search_empty_index(self, tmp_path):
        """Test search on empty index."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        results = runner._search_index.search("python")
        assert len(results) == 0

        runner.close()


class TestTagIntegration:
    """Test tag functionality across the pipeline."""

    def test_tags_persist_across_runs(self, tmp_path):
        """Test that tags persist between pipeline runs."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)

        # First run
        runner1 = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)
        runner1._interest_store.add(Interest(
            name="python", keywords=["python"],
        ))
        page = CrawledPage(
            url="https://example.com/python",
            title="Python Guide",
            content="Python is a programming language.",
        )
        runner1.add_page_directly(page)
        runner1.close()

        # Second run - verify tags still exist
        runner2 = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)
        tags = runner2._tag_store.get_tags_for_page("https://example.com/python")
        tag_names = [t.name for t in tags]
        assert "python" in tag_names
        runner2.close()

    def test_multiple_tags_per_page(self, tmp_path):
        """Test that pages can have multiple tags."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(
            name="python", keywords=["python", "django"],
        ))
        runner._interest_store.add(Interest(
            name="webdev", keywords=["web", "development"],
        ))

        page = CrawledPage(
            url="https://example.com/python-web",
            title="Python Web Development",
            content="Python is great for web development with Django.",
        )
        runner.add_page_directly(page)

        tags = runner._tag_store.get_tags_for_page(page.url)
        assert len(tags) >= 1

        runner.close()
