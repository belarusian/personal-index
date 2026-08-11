"""Integration tests for HTML content processing through the full pipeline."""

from __future__ import annotations

import os

import pytest

from personal_index.config.pipeline_config import PipelineConfig
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import Interest
from personal_index.pipeline_runner import PipelineRunner


class TestHTMLPipelineIntegration:
    """Test HTML content flows through the full pipeline correctly."""

    def test_html_extraction_and_indexing(self, tmp_path):
        """HTML files should be extracted, indexed, and searchable."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.html").write_text(
            "<!DOCTYPE html><html><head><title>Python Tutorial</title></head>"
            "<body><h1>Python Tutorial</h1>"
            "<p>Learn Python programming from scratch. Python is a "
            "versatile language for web development and data science.</p>"
            "<p>Topics covered: variables, functions, classes, modules.</p>"
            "</body></html>"
        )

        runner = PipelineRunner(data_dir=data_dir)
        stats = runner.run_from_files([str(docs / "article.html")])
        runner.close()

        assert stats.pages_indexed == 1

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("python tutorial")
        assert len(results) > 0
        assert "Python Tutorial" in results[0].title

    def test_html_with_scripts_and_styles_filtered(self, tmp_path):
        """HTML with scripts/styles should extract only body content."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "page.html").write_text(
            "<html><head><title>Clean Content</title>"
            "<script>var x = 'this should not appear';</script>"
            "<style>.hidden { display: none; }</style></head>"
            "<body><p>This is the visible content that matters.</p>"
            "</body></html>"
        )

        runner = PipelineRunner(data_dir=data_dir)
        stats = runner.run_from_files([str(docs / "page.html")])
        runner.close()

        assert stats.pages_indexed == 1
        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("visible content")
        assert len(results) > 0

    def test_multiple_html_files_pipeline(self, tmp_path):
        """Multiple HTML files should all be processed."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        for i, topic in enumerate(["python", "javascript", "rust"]):
            (docs / f"{topic}.html").write_text(
                f"<html><head><title>{topic.title()} Guide</title></head>"
                f"<body><h1>{topic.title()} Guide</h1>"
                f"<p>Learn {topic} programming. {topic} is a great language.</p>"
                f"</body></html>"
            )

        runner = PipelineRunner(data_dir=data_dir)
        stats = runner.run_from_files([
            str(docs / f"{t}.html") for t in ["python", "javascript", "rust"]
        ])
        runner.close()

        assert stats.pages_indexed == 3

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        for topic in ["python", "javascript", "rust"]:
            results = index.search(topic)
            assert len(results) > 0, f"Should find results for {topic}"

    def test_html_with_interest_matching(self, tmp_path):
        """HTML content should match interests and get higher scores."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        interest_store = InterestStore(
            store_path=os.path.join(data_dir, "interests.json")
        )
        interest_store.add(Interest(
            name="webdev", keywords=["web", "development", "javascript"]
        ))

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "web.html").write_text(
            "<html><body>"
            "<h1>Web Development Guide</h1>"
            "<p>Modern web development with JavaScript frameworks.</p>"
            "</body></html>"
        )
        (docs / "unrelated.html").write_text(
            "<html><body>"
            "<h1>Fishing Tips</h1>"
            "<p>Best fishing spots and techniques for beginners.</p>"
            "</body></html>"
        )

        runner = PipelineRunner(data_dir=data_dir)
        stats = runner.run_from_files([
            str(docs / "web.html"),
            str(docs / "unrelated.html"),
        ])
        runner.close()

        assert stats.interests_matched > 0
        assert stats.pages_indexed == 2
