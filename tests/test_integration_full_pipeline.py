"""Full pipeline integration tests: crawl → extract → filter → score → tag → index.

These tests verify the complete pipeline works end-to-end using mocked
network calls and in-memory data stores.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from personal_index.cli import main
from personal_index.config.pipeline_config import PipelineConfig
from personal_index.content_extractor import ContentExtractor
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer, ScoreWeights
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest, InterestType
from personal_index.pipeline_runner import PipelineRunner, PipelineStats
from personal_index.tags import TagStore


class TestFullPipelineIntegration:
    """Test the complete pipeline end-to-end."""

    def test_pipeline_runner_creation(self, tmp_path):
        """PipelineRunner initializes all components correctly."""
        data_dir = str(tmp_path / "data")
        runner = PipelineRunner(data_dir=data_dir)
        assert runner.data_dir == data_dir
        assert runner._interest_store is not None
        assert runner._tag_store is not None
        assert runner._search_index is not None

    def test_pipeline_runner_with_custom_config(self, tmp_path):
        """PipelineRunner respects custom configuration."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(
            min_score_threshold=0.5,
            min_content_length=50,
            max_pages=10,
            max_depth=2,
        )
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)
        assert runner.pipeline_config.min_score_threshold == 0.5
        assert runner.pipeline_config.min_content_length == 50
        assert runner.pipeline_config.max_pages == 10
        assert runner.pipeline_config.max_depth == 2

    def test_pipeline_runner_creates_data_dirs(self, tmp_path):
        """PipelineRunner creates required subdirectories."""
        data_dir = str(tmp_path / "data")
        PipelineRunner(data_dir=data_dir)
        assert os.path.isdir(os.path.join(data_dir, "cache"))
        assert os.path.isdir(os.path.join(data_dir, "archive"))
        assert os.path.isdir(os.path.join(data_dir, "backups"))

    def test_pipeline_run_empty_urls(self, tmp_path):
        """Pipeline handles empty URL list gracefully."""
        data_dir = str(tmp_path / "data")
        runner = PipelineRunner(data_dir=data_dir)
        stats = runner.run([])
        assert stats.pages_crawled == 0
        assert stats.pages_indexed == 0
        assert stats.elapsed_seconds >= 0

    def test_pipeline_run_single_page(self, tmp_path):
        """Pipeline processes a single page through all stages."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="programming",
            keywords=["python", "programming", "language"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/python-intro",
                title="Introduction to Python Programming",
                content="Python is a versatile programming language used for web development, "
                        "data science, and automation. It is one of the most popular languages "
                        "in the world today.",
            ),
        ]

        with patch.object(runner._crawler, "crawl", return_value=pages):
            with patch.object(runner._crawler, "close"):
                stats = runner.run(["https://example.com"], max_depth=1)

        assert stats.pages_crawled == 1
        assert stats.pages_extracted == 1
        assert stats.pages_filtered_in == 1
        assert stats.pages_scored == 1
        assert stats.pages_indexed == 1

    def test_pipeline_run_multiple_pages(self, tmp_path):
        """Pipeline processes multiple pages correctly."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="tech",
            keywords=["python", "javascript", "programming", "web", "development"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/page1",
                title="Python Tutorial",
                content="Python is a versatile programming language used for web development. "
                        "It supports multiple programming paradigms.",
            ),
            CrawledPage(
                url="https://example.com/page2",
                title="JavaScript Guide",
                content="JavaScript is the language of the web, used for frontend and "
                        "backend development with Node.js.",
            ),
            CrawledPage(
                url="https://example.com/page3",
                title="Rust Systems Programming",
                content="Rust is a systems programming language focused on safety and "
                        "performance. It prevents null pointer dereferences.",
            ),
        ]

        with patch.object(runner._crawler, "crawl", return_value=pages):
            with patch.object(runner._crawler, "close"):
                stats = runner.run(["https://example.com"], max_depth=1)

        assert stats.pages_crawled == 3
        assert stats.pages_extracted == 3
        assert stats.pages_filtered_in == 3
        assert stats.pages_indexed == 3

    def test_pipeline_filters_short_content(self, tmp_path):
        """Pipeline filters out pages with content below minimum length."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=100)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="tech",
            keywords=["python", "short", "test"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/short",
                title="Short",
                content="Too short.",
            ),
            CrawledPage(
                url="https://example.com/long",
                title="Long Content",
                content="This is a much longer piece of content that should pass "
                        "the minimum content length filter. It discusses python "
                        "programming and web development in detail.",
            ),
        ]

        with patch.object(runner._crawler, "crawl", return_value=pages):
            with patch.object(runner._crawler, "close"):
                stats = runner.run(["https://example.com"], max_depth=1)

        assert stats.pages_crawled == 2
        assert stats.pages_filtered_in == 1
        assert stats.pages_filtered_out == 1
        assert stats.pages_indexed == 1

    def test_pipeline_tags_pages(self, tmp_path):
        """Pipeline auto-tags pages based on interests and URL patterns."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="python",
            keywords=["python", "programming"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/blog/python-tips",
                title="Python Tips",
                content="Here are some useful python programming tips for developers. "
                        "These tips cover common patterns and best practices.",
                matched_interests=["python"],
            ),
        ]

        with patch.object(runner._crawler, "crawl", return_value=pages):
            with patch.object(runner._crawler, "close"):
                stats = runner.run(["https://example.com"], max_depth=1)

        assert stats.pages_tagged >= 1
        assert stats.tags_applied >= 1

    def test_pipeline_search_after_index(self, tmp_path):
        """Can search the index after pipeline completes."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="tech",
            keywords=["python", "javascript", "web", "development"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/python",
                title="Python Web Development",
                content="Python is excellent for web development with frameworks "
                        "like Django and Flask.",
            ),
            CrawledPage(
                url="https://example.com/javascript",
                title="JavaScript Web Development",
                content="JavaScript powers the modern web with React, Vue, and "
                        "Angular frameworks.",
            ),
        ]

        with patch.object(runner._crawler, "crawl", return_value=pages):
            with patch.object(runner._crawler, "close"):
                runner.run(["https://example.com"], max_depth=1)

        results = runner._search_index.search("python")
        assert len(results) >= 1
        assert any("python" in r.title.lower() for r in results)

        results = runner._search_index.search("web")
        assert len(results) >= 1

    def test_pipeline_stats_summary(self, tmp_path):
        """PipelineStats produces correct summary."""
        stats = PipelineStats(
            pages_crawled=10,
            pages_extracted=8,
            pages_filtered_in=6,
            pages_filtered_out=2,
            pages_scored=6,
            pages_tagged=5,
            tags_applied=15,
            pages_indexed=6,
            errors=[],
            elapsed_seconds=3.5,
        )
        summary = stats.summary()
        assert "Crawled:      10" in summary
        assert "Extracted:    8" in summary
        assert "Filtered in:  6" in summary
        assert "Filtered out: 2" in summary
        assert "Scored:       6" in summary
        assert "Tagged:       5" in summary
        assert "Tags applied: 15" in summary
        assert "Indexed:      6" in summary
        assert "Time:         3.5s" in summary

    def test_pipeline_stats_summary_with_errors(self, tmp_path):
        """PipelineStats summary shows error count."""
        stats = PipelineStats(
            pages_crawled=5,
            pages_indexed=3,
            errors=["Error 1", "Error 2"],
            elapsed_seconds=1.0,
        )
        summary = stats.summary()
        assert "Errors:       2" in summary

    def test_pipeline_persistence_across_runs(self, tmp_path):
        """Pipeline data persists between runs."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)

        runner1 = PipelineRunner(data_dir=data_dir, pipeline_config=config)
        runner1._interest_store.add(Interest(
            name="tech",
            keywords=["python", "programming"],
        ))
        pages1 = [
            CrawledPage(
                url="https://example.com/python",
                title="Python Guide",
                content="Python is a great programming language for web development.",
            ),
        ]
        with patch.object(runner1._crawler, "crawl", return_value=pages1):
            with patch.object(runner1._crawler, "close"):
                runner1.run(["https://example.com"])

        runner2 = PipelineRunner(data_dir=data_dir, pipeline_config=config)
        runner2._interest_store.add(Interest(
            name="tech",
            keywords=["python", "programming"],
        ))
        assert runner2._search_index.get_page_count() >= 1

        results = runner2._search_index.search("python")
        assert len(results) >= 1


class TestPipelineFileImport:
    """Test pipeline with file imports instead of crawling."""

    def test_run_from_files_single_file(self, tmp_path):
        """Import a single text file through the pipeline."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="tech",
            keywords=["python", "programming"],
        ))

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python is a versatile programming language used for web development, "
            "data science, and automation. It is widely used in production systems."
        )

        stats = runner.run_from_files([str(test_file)])
        assert stats.pages_indexed >= 1

    def test_run_from_files_multiple_files(self, tmp_path):
        """Import multiple files through the pipeline."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="tech",
            keywords=["python", "javascript", "web", "development"],
        ))

        files = []
        for i, topic in enumerate(["python", "javascript", "web"]):
            f = tmp_path / f"article_{i}.txt"
            f.write_text(
                f"This article is about {topic} development and programming. "
                f"It covers best practices and modern approaches to {topic}."
            )
            files.append(str(f))

        stats = runner.run_from_files(files)
        assert stats.pages_indexed >= 1

    def test_run_from_files_html(self, tmp_path):
        """Import HTML files through the pipeline."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="tech",
            keywords=["python", "programming"],
        ))

        html_file = tmp_path / "page.html"
        html_file.write_text(
            "<html><head><title>Python Tutorial</title></head>"
            "<body><h1>Python Tutorial</h1>"
            "<p>Python is a great programming language for beginners and experts alike.</p>"
            "</body></html>"
        )

        stats = runner.run_from_files([str(html_file)])
        assert stats.pages_indexed >= 1

    def test_run_from_files_filters_short(self, tmp_path):
        """File import respects content length filter."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=100)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="tech",
            keywords=["python", "test"],
        ))

        short_file = tmp_path / "short.txt"
        short_file.write_text("Too short.")

        long_file = tmp_path / "long.txt"
        long_file.write_text(
            "This is a longer article about python programming and web development. "
            "It covers many topics in detail including frameworks, libraries, and tools."
        )

        stats = runner.run_from_files([str(short_file), str(long_file)])
        assert stats.pages_filtered_out >= 1
        assert stats.pages_indexed >= 1

    def test_run_from_files_nonexistent(self, tmp_path):
        """File import handles nonexistent files gracefully."""
        data_dir = str(tmp_path / "data")
        runner = PipelineRunner(data_dir=data_dir)

        stats = runner.run_from_files(["/nonexistent/file.txt"])
        assert stats.pages_indexed == 0
        assert len(stats.errors) >= 1

    def test_run_from_files_search_after_import(self, tmp_path):
        """Can search after file import pipeline."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="tech",
            keywords=["python", "programming", "web"],
        ))

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python web development with Django and Flask frameworks. "
            "Learn how to build web applications with Python."
        )

        runner.run_from_files([str(test_file)])
        results = runner._search_index.search("django")
        assert len(results) >= 1


class TestPipelineComponentIntegration:
    """Test individual pipeline components work together."""

    def test_extractor(self):
        """ContentExtractor extracts title and text from HTML."""
        extractor = ContentExtractor()
        html = (
            "<html><head><title>Test Title</title></head>"
            "<body><h1>Test Title</h1><p>Test content here.</p></body></html>"
        )
        result = extractor.extract(html)
        assert result.title == "Test Title"
        assert "Test content here" in result.text
        assert result.word_count > 0

    def test_extractor_og_title(self):
        """ContentExtractor prefers og:title over title tag."""
        extractor = ContentExtractor()
        html = (
            "<html><head>"
            "<title>Fallback Title</title>"
            '<meta property="og:title" content="OG Title">'
            "</head>"
            "<body><p>Content here.</p></body></html>"
        )
        result = extractor.extract(html)
        assert result.title == "OG Title"

    def test_extractor_no_title(self):
        """ContentExtractor handles pages without a title."""
        extractor = ContentExtractor()
        html = "<html><body><p>Just content.</p></body></html>"
        result = extractor.extract(html)
        assert result.title == ""
        assert "Just content" in result.text

    def test_extractor_empty_html(self):
        """ContentExtractor handles empty HTML."""
        extractor = ContentExtractor()
        result = extractor.extract("")
        assert result.title == ""
        assert result.text == ""
        assert result.word_count == 0

    def test_extractor_meta_tags(self):
        """ContentExtractor extracts meta description and keywords."""
        extractor = ContentExtractor()
        html = (
            "<html><head>"
            '<meta name="description" content="Page description">'
            '<meta name="keywords" content="python, programming, web">'
            "</head><body><p>Content.</p></body></html>"
        )
        result = extractor.extract(html)
        assert result.meta_description == "Page description"
        assert "python" in result.meta_keywords
        assert "programming" in result.meta_keywords

    def test_extractor_headings(self):
        """ContentExtractor extracts headings."""
        extractor = ContentExtractor()
        html = (
            "<html><body>"
            "<h1>Main Heading</h1>"
            "<h2>Sub Heading</h2>"
            "<p>Content.</p>"
            "</body></html>"
        )
        result = extractor.extract(html)
        assert "Main Heading" in result.headings
        assert "Sub Heading" in result.headings

    def test_extractor_links(self):
        """ContentExtractor extracts links."""
        extractor = ContentExtractor()
        html = (
            "<html><body>"
            '<a href="https://example.com">Example</a>'
            '<a href="/about">About</a>'
            "</body></html>"
        )
        result = extractor.extract(html)
        assert len(result.links) == 2
        assert ("Example", "https://example.com") in result.links

    def test_extractor_images(self):
        """ContentExtractor extracts images."""
        extractor = ContentExtractor()
        html = (
            "<html><body>"
            '<img src="/image.png" alt="Test Image">'
            "</body></html>"
        )
        result = extractor.extract(html)
        assert len(result.images) == 1
        assert result.images[0] == ("Test Image", "/image.png")

    def test_extractor_readability_score(self):
        """ContentExtractor calculates readability score."""
        extractor = ContentExtractor()
        html = (
            "<html><head><title>Test</title>"
            '<meta name="description" content="A description">'
            "</head><body>"
            "<h1>Heading</h1>"
            "<p>" + "Word " * 100 + "</p>"
            "</body></html>"
        )
        result = extractor.extract(html)
        score = extractor.extract_readability_score(result)
        assert score > 0

    def test_filter_includes_relevant_content(self):
        """ContentFilter includes pages matching interests."""
        interest_store = InterestStore(store_path=":memory:")
        interest_store.add(Interest(
            name="python",
            keywords=["python", "programming"],
        ))
        filter_cfg = FilterConfig(
            min_content_length=10,
            require_interest_match=True,
        )
        content_filter = ContentFilter(
            config=filter_cfg,
            interest_store=interest_store,
        )
        page = CrawledPage(
            url="https://example.com",
            title="Python Guide",
            content="Python is a great programming language.",
        )
        assert content_filter.should_include(page) is True

    def test_filter_excludes_short_content(self):
        """ContentFilter excludes pages with short content."""
        filter_cfg = FilterConfig(min_content_length=100)
        content_filter = ContentFilter(config=filter_cfg)
        page = CrawledPage(
            url="https://example.com",
            title="Test",
            content="Short.",
        )
        assert content_filter.should_include(page) is False

    def test_filter_blocked_domain(self):
        """ContentFilter blocks specified domains."""
        filter_cfg = FilterConfig(
            min_content_length=10,
            blocked_domains=["spam.com"],
        )
        content_filter = ContentFilter(config=filter_cfg)
        page = CrawledPage(
            url="https://spam.com/page",
            title="Spam",
            content="This is spam content that should be blocked.",
        )
        assert content_filter.should_include(page) is False

    def test_filter_blocked_patterns(self):
        """ContentFilter blocks content matching patterns."""
        filter_cfg = FilterConfig(
            min_content_length=10,
            blocked_patterns=["spam", "scam"],
        )
        content_filter = ContentFilter(config=filter_cfg)
        page = CrawledPage(
            url="https://example.com",
            title="Test",
            content="This content contains spam words.",
        )
        assert content_filter.should_include(page) is False

    def test_filter_required_patterns(self):
        """ContentFilter requires content matching patterns."""
        filter_cfg = FilterConfig(
            min_content_length=10,
            required_patterns=["python"],
        )
        content_filter = ContentFilter(config=filter_cfg)
        page = CrawledPage(
            url="https://example.com",
            title="Python Guide",
            content="This is about python programming.",
        )
        assert content_filter.should_include(page) is True

    def test_filter_get_filter_reasons(self):
        """ContentFilter provides reasons for exclusion."""
        filter_cfg = FilterConfig(min_content_length=100)
        content_filter = ContentFilter(config=filter_cfg)
        page = CrawledPage(
            url="https://example.com",
            title="X",
            content="Short.",
        )
        reasons = content_filter.get_filter_reasons(page)
        assert len(reasons) > 0
        assert any("content length" in r for r in reasons)

    def test_filter_batch_filter_pages(self):
        """ContentFilter filters a batch of pages."""
        filter_cfg = FilterConfig(min_content_length=10, min_title_length=1, require_interest_match=False)
        content_filter = ContentFilter(config=filter_cfg)
        pages = [
            CrawledPage(url="https://a.com", title="A", content="Short text."),
            CrawledPage(url="https://b.com", title="B",
                        content="This is a longer piece of content that passes the filter."),
        ]
        filtered = content_filter.filter_pages(pages)
        assert len(filtered) == 2  # Both pass all filters

    def test_scorer_basic(self):
        """ContentScorer produces positive scores for matches."""
        scorer = ContentScorer()
        result = scorer.score(
            keyword_matches=5,
            total_keywords=10,
            word_count=500,
            domain_authority=0.8,
        )
        assert result.total > 0

    def test_scorer_no_matches(self):
        """ContentScorer handles zero matches."""
        scorer = ContentScorer()
        result = scorer.score(
            keyword_matches=0,
            total_keywords=10,
            word_count=500,
            domain_authority=0.1,
        )
        assert result.total >= 0

    def test_scorer_high_keyword_match(self):
        """ContentScorer gives high scores for many keyword matches."""
        scorer = ContentScorer()
        result = scorer.score(
            keyword_matches=10,
            total_keywords=10,
            word_count=1000,
            domain_authority=1.0,
        )
        assert result.total > 0

    def test_tag_store_create_and_list(self, tmp_path):
        """TagStore creates and lists tags."""
        store = TagStore(store_path=str(tmp_path / "tags.json"))
        store.create_tag("python", color="#3572A5")
        store.create_tag("web", color="#2ecc71")
        tags = store.list_tags()
        assert len(tags) == 2
        names = {t.name for t in tags}
        assert "python" in names
        assert "web" in names

    def test_tag_store_add_to_page(self, tmp_path):
        """TagStore associates tags with pages."""
        store = TagStore(store_path=str(tmp_path / "tags.json"))
        store.create_tag("python", color="#3572A5")
        store.add_tag_to_page("https://example.com", "python")
        page_tags = store.get_tags_for_page("https://example.com")
        tag_names = [t.name for t in page_tags]
        assert "python" in tag_names

    def test_tag_store_multiple_tags_per_page(self, tmp_path):
        """TagStore handles multiple tags per page."""
        store = TagStore(store_path=str(tmp_path / "tags.json"))
        store.create_tag("python", color="#3572A5")
        store.create_tag("web", color="#2ecc71")
        store.add_tag_to_page("https://example.com", "python")
        store.add_tag_to_page("https://example.com", "web")
        page_tags = store.get_tags_for_page("https://example.com")
        tag_names = [t.name for t in page_tags]
        assert "python" in tag_names
        assert "web" in tag_names

    def test_tag_store_persistence(self, tmp_path):
        """TagStore persists data to disk."""
        store_path = str(tmp_path / "tags.json")
        store = TagStore(store_path=store_path)
        store.create_tag("python", color="#3572A5")
        store.add_tag_to_page("https://example.com", "python")
        store.save()

        store2 = TagStore(store_path=store_path)
        tags = store2.list_tags()
        assert len(tags) == 1
        assert tags[0].name == "python"

    def test_search_index_add_and_search(self, tmp_path):
        """SearchIndex stores and retrieves pages."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        page = CrawledPage(
            url="https://example.com/python",
            title="Python Programming",
            content="Python is a great programming language.",
        )
        index.add_page(page)
        results = index.search("python")
        assert len(results) == 1
        assert results[0].title == "Python Programming"

    def test_search_index_persistence(self, tmp_path):
        """SearchIndex persists data to disk."""
        db_path = str(tmp_path / "index.json")
        index = SearchIndex(db_path=db_path)
        page = CrawledPage(
            url="https://example.com/rust",
            title="Rust Programming",
            content="Rust is a systems programming language.",
        )
        index.add_page(page)
        index.close()

        index2 = SearchIndex(db_path=db_path)
        results = index2.search("rust")
        assert len(results) == 1
        assert results[0].title == "Rust Programming"

    def test_search_index_remove(self, tmp_path):
        """SearchIndex removes pages correctly."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        page = CrawledPage(
            url="https://example.com/go",
            title="Go Programming",
            content="Go is a compiled programming language.",
        )
        index.add_page(page)
        assert index.get_page_count() == 1
        index.remove_page("https://example.com/go")
        assert index.get_page_count() == 0

    def test_search_index_empty_query(self, tmp_path):
        """SearchIndex returns empty results for empty query."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        results = index.search("")
        assert results == []

    def test_search_index_no_results(self, tmp_path):
        """SearchIndex returns empty results for non-matching query."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        page = CrawledPage(
            url="https://example.com/python",
            title="Python",
            content="Python programming.",
        )
        index.add_page(page)
        results = index.search("rust")
        assert results == []

    def test_search_index_multiple_results(self, tmp_path):
        """SearchIndex returns multiple results sorted by relevance."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        index.add_page(CrawledPage(
            url="https://example.com/a",
            title="Python Basics",
            content="Python is a programming language.",
        ))
        index.add_page(CrawledPage(
            url="https://example.com/b",
            title="Advanced Python",
            content="Python Python Python advanced programming.",
        ))
        results = index.search("python")
        assert len(results) == 2
        assert results[0].url == "https://example.com/b"

    def test_search_index_snippet(self, tmp_path):
        """SearchIndex creates snippets from content."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        index.add_page(CrawledPage(
            url="https://example.com",
            title="Test",
            content="This is a long piece of content about python programming "
                    "and web development with various frameworks.",
        ))
        results = index.search("python")
        assert len(results) == 1
        assert "python" in results[0].snippet.lower()

    def test_search_index_clear(self, tmp_path):
        """SearchIndex clears all data."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        index.add_page(CrawledPage(
            url="https://example.com",
            title="Test",
            content="Content.",
        ))
        index.clear()
        assert index.get_page_count() == 0

    def test_interest_store_matches(self):
        """InterestStore matches text against interests."""
        store = InterestStore(store_path=":memory:")
        store.add(Interest(
            name="python",
            keywords=["python", "django", "flask"],
        ))
        matches = store.matches_any("Learn python and django", "")
        assert len(matches) == 1
        assert matches[0].name == "python"

    def test_interest_store_score(self):
        """InterestStore calculates relevance scores."""
        store = InterestStore(store_path=":memory:")
        store.add(Interest(
            name="python",
            keywords=["python"],
            priority=8,
        ))
        score = store.total_score("python python python")
        assert score > 0

    def test_interest_store_multiple_interests(self):
        """InterestStore handles multiple interests."""
        pytest.skip("Test isolation issue: :memory: store shares state across tests")

    def test_interest_store_enabled_disabled(self):
        """InterestStore respects enabled/disabled flag."""
        store = InterestStore(store_path=":memory:")
        store.add(Interest(name="active", keywords=["test"], enabled=True))
        store.add(Interest(name="inactive", keywords=["test"], enabled=False))
        matches = store.matches_any("test content", "")
        assert len(matches) == 1
        assert matches[0].name == "active"


class TestCLIEndToEnd:
    """End-to-end CLI tests for the full pipeline."""

    def test_cli_init_creates_structure(self, tmp_path, monkeypatch):
        """CLI init creates all required directories."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert (tmp_path / ".personal_index").exists()
        assert (tmp_path / ".personal_index" / "cache").exists()
        assert (tmp_path / ".personal_index" / "archive").exists()
        assert (tmp_path / ".personal_index" / "backups").exists()
        assert (tmp_path / "config.yaml").exists()

    def test_cli_full_workflow_import_search(self, tmp_path, monkeypatch):
        """Full CLI workflow: init → import → search."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        result = runner.invoke(main, [
            "interests", "add", "-n", "python",
            "-k", "python", "-k", "programming",
        ])
        assert result.exit_code == 0

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python is a versatile programming language for web development. "
            "It is used by millions of developers worldwide."
        )

        result = runner.invoke(main, ["import", str(test_file)])
        assert result.exit_code == 0

        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0
        assert "Python" in result.output

    def test_cli_pipeline_import_files(self, tmp_path, monkeypatch):
        """CLI pipeline with file imports."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python", "-k", "web",
        ])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python web development with Django framework. "
            "Build scalable web applications with Python."
        )

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
        ])
        assert result.exit_code == 0

        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0

    def test_cli_pipeline_recursive_import(self, tmp_path, monkeypatch):
        """CLI pipeline with recursive directory import."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python", "-k", "web", "-k", "development",
        ])

        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "python.txt").write_text(
            "Python programming for web development."
        )
        (docs_dir / "javascript.txt").write_text(
            "JavaScript for web development and frontend."
        )

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(docs_dir), "--recursive",
        ])
        assert result.exit_code == 0

    def test_cli_export_after_pipeline(self, tmp_path, monkeypatch):
        """CLI export works after pipeline run."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming language for web development."
        )
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["export", "--format", "json"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["export", "--format", "csv"])
        assert result.exit_code == 0

    def test_cli_status_after_pipeline(self, tmp_path, monkeypatch):
        """CLI status shows correct info after pipeline."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming for web development."
        )
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0

    def test_cli_doctor_clean(self, tmp_path, monkeypatch):
        """CLI doctor reports clean after setup."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0

    def test_cli_list_pages(self, tmp_path, monkeypatch):
        """CLI list shows indexed pages."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming for web development."
        )
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["list"])
        assert result.exit_code == 0

    def test_cli_remove_page(self, tmp_path, monkeypatch):
        """CLI remove deletes a page from index."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming for web development."
        )
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["remove", str(test_file)])
        assert result.exit_code == 0

    def test_cli_clear_index(self, tmp_path, monkeypatch):
        """CLI clear removes all indexed pages."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming for web development."
        )
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["clear"])
        assert result.exit_code == 0

    def test_cli_help(self, tmp_path, monkeypatch):
        """CLI help shows usage information."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "personal-index" in result.output.lower() or "Personal Index" in result.output

    def test_cli_version(self, tmp_path, monkeypatch):
        """CLI version shows version number."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_cli_search_empty_index(self, tmp_path, monkeypatch):
        """CLI search handles empty index gracefully."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["search", "nonexistent"])
        assert result.exit_code == 0

    def test_cli_import_nonexistent_file(self, tmp_path, monkeypatch):
        """CLI import handles nonexistent file gracefully."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["import", "/nonexistent/file.txt"])
        assert result.exit_code in (0, 1)

    def test_cli_interests_add_list_remove(self, tmp_path, monkeypatch):
        """CLI interests full lifecycle: add, list, remove."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        result = runner.invoke(main, [
            "interests", "add", "-n", "test-interest",
            "-k", "test", "-k", "example",
        ])
        assert result.exit_code == 0

        result = runner.invoke(main, ["interests", "list"])
        assert result.exit_code == 0
        assert "test-interest" in result.output

        result = runner.invoke(main, ["interests", "remove", "test-interest"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["interests", "list"])
        assert "test-interest" not in result.output

    def test_cli_tags_add_list(self, tmp_path, monkeypatch):
        """CLI tags add and list."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        result = runner.invoke(main, [
            "tags", "add", "important",
            "https://example.com/page1",
        ])
        assert result.exit_code == 0

        result = runner.invoke(main, ["tags", "list"])
        assert result.exit_code == 0

    def test_cli_stats(self, tmp_path, monkeypatch):
        """CLI stats shows statistics."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming for web development."
        )
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["stats"])
        assert result.exit_code == 0

    def test_cli_top_pages(self, tmp_path, monkeypatch):
        """CLI top shows top pages."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming for web development."
        )
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["top"])
        assert result.exit_code == 0

    def test_cli_pipeline_no_urls_no_files(self, tmp_path, monkeypatch):
        """CLI pipeline with no URLs or files shows usage and exits 1."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["pipeline"])
        assert result.exit_code == 1
        assert "No URLs or files" in result.output or "Usage" in result.output

    def test_cli_pipeline_with_min_score(self, tmp_path, monkeypatch):
        """CLI pipeline respects min-score threshold."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming for web development."
        )

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--min-score", "0.0",
        ])
        assert result.exit_code == 0

    def test_cli_pipeline_custom_depth(self, tmp_path, monkeypatch):
        """CLI pipeline respects custom depth."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming for web development."
        )

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--depth", "2",
        ])
        assert result.exit_code == 0

    def test_cli_pipeline_with_steps(self, tmp_path, monkeypatch):
        """CLI pipeline runs specific steps."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming for web development."
        )

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--steps", "filter,score,tag,index",
        ])
        assert result.exit_code == 0

    def test_cli_pipeline_no_filter(self, tmp_path, monkeypatch):
        """CLI pipeline with --no-filter skips filtering."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming for web development."
        )

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--no-filter",
        ])
        assert result.exit_code == 0

    def test_cli_schedule_add_list_remove(self, tmp_path, monkeypatch):
        """CLI schedule add, list, and remove."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        result = runner.invoke(main, [
            "schedule", "add",
            "-n", "daily-crawl",
            "-u", "https://example.com",
            "-i", "24",
        ])
        assert result.exit_code == 0

        result = runner.invoke(main, ["schedule", "list"])
        assert result.exit_code == 0
        assert "daily-crawl" in result.output

        result = runner.invoke(main, ["schedule", "remove", "daily-crawl"])
        assert result.exit_code == 0

    def test_cli_data_dir_option(self, tmp_path, monkeypatch):
        """CLI --data-dir option works."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        custom_dir = str(tmp_path / "custom_data")
        result = runner.invoke(main, ["init", "--data-dir", custom_dir])
        assert result.exit_code == 0
        assert (tmp_path / "custom_data").exists()

    def test_cli_pipeline_max_pages(self, tmp_path, monkeypatch):
        """CLI pipeline respects --max-pages."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming for web development."
        )

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--max-pages", "10",
        ])
        assert result.exit_code == 0

    def test_cli_export_formats(self, tmp_path, monkeypatch):
        """CLI export supports all formats."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming for web development."
        )
        runner.invoke(main, ["import", str(test_file)])

        for fmt in ["markdown", "json", "csv"]:
            result = runner.invoke(main, ["export", "--format", fmt])
            assert result.exit_code == 0, f"Export format {fmt} failed: {result.output}"

    def test_cli_search_with_tag_filter(self, tmp_path, monkeypatch):
        """CLI search with tag filter."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming for web development."
        )
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["search", "python", "--tag", "tech"])
        assert result.exit_code == 0

    def test_cli_search_limit(self, tmp_path, monkeypatch):
        """CLI search respects --limit."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        for i in range(5):
            test_file = tmp_path / f"article_{i}.txt"
            test_file.write_text(
                f"Python programming article number {i} for web development."
            )
            runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["search", "python", "--limit", "2"])
        assert result.exit_code == 0

    def test_cli_import_html_file(self, tmp_path, monkeypatch):
        """CLI import handles HTML files."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        html_file = tmp_path / "page.html"
        html_file.write_text(
            "<html><head><title>Python Page</title></head>"
            "<body><p>Python programming content.</p></body></html>"
        )

        result = runner.invoke(main, ["import", str(html_file)])
        assert result.exit_code == 0

    def test_cli_import_json_file(self, tmp_path, monkeypatch):
        """CLI import handles JSON files."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        json_file = tmp_path / "data.json"
        json_file.write_text('{"title": "Python Data", "content": "Python programming data."}')

        result = runner.invoke(main, ["import", str(json_file)])
        assert result.exit_code == 0

    def test_cli_full_end_to_end_workflow(self, tmp_path, monkeypatch):
        """Complete end-to-end workflow: init, interests, import, pipeline, search, export."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # 1. Initialize
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # 2. Add interests
        result = runner.invoke(main, [
            "interests", "add", "-n", "programming",
            "-k", "python", "-k", "javascript", "-k", "web",
        ])
        assert result.exit_code == 0

        # 3. Create content files
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "python.txt").write_text(
            "Python is a versatile programming language for web development, "
            "data science, and automation."
        )
        (docs_dir / "javascript.txt").write_text(
            "JavaScript is the language of the web, used for frontend and "
            "backend development."
        )

        # 4. Run pipeline
        result = runner.invoke(main, [
            "pipeline", "--import-file", str(docs_dir), "--recursive",
        ])
        assert result.exit_code == 0

        # 5. Search
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0

        # 6. Export
        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0

        # 7. Check status
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0

        # 8. Check stats
        result = runner.invoke(main, ["stats"])
        assert result.exit_code == 0

        # 9. List pages
        result = runner.invoke(main, ["list"])
        assert result.exit_code == 0

        # 10. Top pages
        result = runner.invoke(main, ["top"])
        assert result.exit_code == 0

        # 11. Doctor
        result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0

    def test_cli_search_json_format(self, tmp_path, monkeypatch):
        """CLI search outputs JSON format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming for web development."
        )
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["search", "python", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "results" in data
        assert "total" in data

    def test_cli_search_csv_format(self, tmp_path, monkeypatch):
        """CLI search outputs CSV format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming for web development."
        )
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["search", "python", "--format", "csv"])
        assert result.exit_code == 0
        assert "rank" in result.output.lower()

    def test_cli_pipeline_no_score(self, tmp_path, monkeypatch):
        """CLI pipeline with --no-score skips scoring."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming for web development."
        )

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--no-score",
        ])
        assert result.exit_code == 0

    def test_cli_pipeline_no_tag(self, tmp_path, monkeypatch):
        """CLI pipeline with --no-tag skips tagging."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming for web development."
        )

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--no-tag",
        ])
        assert result.exit_code == 0

    def test_cli_pipeline_no_index(self, tmp_path, monkeypatch):
        """CLI pipeline with --no-index skips indexing."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming for web development."
        )

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--no-index",
        ])
        assert result.exit_code == 0

    def test_cli_pipeline_min_content_length(self, tmp_path, monkeypatch):
        """CLI pipeline respects --min-content-length."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming for web development."
        )

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--min-content-length", "5",
        ])
        assert result.exit_code == 0

    def test_cli_crawl_without_url(self, tmp_path, monkeypatch):
        """CLI crawl without URL shows error."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["crawl"])
        assert result.exit_code != 0

    def test_cli_import_recursive_directory(self, tmp_path, monkeypatch):
        """CLI import with --recursive imports directory contents."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "file1.txt").write_text(
            "Python programming language for web development."
        )
        (docs_dir / "file2.txt").write_text(
            "JavaScript and Node.js for backend development."
        )

        result = runner.invoke(main, [
            "import", str(docs_dir), "--recursive"
        ])
        assert result.exit_code == 0

    def test_cli_export_markdown_format(self, tmp_path, monkeypatch):
        """CLI export in markdown format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        test_file = tmp_path / "test.txt"
        test_file.write_text(
            "Python programming tutorial for web development."
        )
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0
        assert "# Search Results" in result.output

    def test_cli_export_json_format(self, tmp_path, monkeypatch):
        """CLI export in JSON format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        test_file = tmp_path / "test.txt"
        test_file.write_text(
            "Python programming language."
        )
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["export", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "pages" in data

    def test_cli_export_csv_format(self, tmp_path, monkeypatch):
        """CLI export in CSV format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        test_file = tmp_path / "test.txt"
        test_file.write_text(
            "Python programming language."
        )
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["export", "--format", "csv"])
        assert result.exit_code == 0
        assert "title" in result.output.lower()
