"""Stress and edge case integration tests for the pipeline.

Tests the pipeline under various stress conditions and edge cases
to ensure robustness.
"""

from __future__ import annotations

import os

import pytest

from personal_index.config.pipeline_config import PipelineConfig
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import Interest
from personal_index.pipeline_runner import PipelineRunner


class TestPipelineStress:
    """Test pipeline under stress conditions."""

    def test_pipeline_many_files(self, tmp_path):
        """Pipeline should handle many files efficiently."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        for i in range(50):
            (docs / f"article_{i}.txt").write_text(
                f"Article {i} about programming and software development. "
                f"This article covers topic number {i} in detail."
            )

        runner = PipelineRunner(data_dir=data_dir)
        stats = runner.run_from_files([
            str(docs / f"article_{i}.txt") for i in range(50)
        ])
        runner.close()

        assert stats.pages_indexed == 50
        assert len(stats.errors) == 0

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        assert index.get_page_count() == 50

    def test_pipeline_large_content(self, tmp_path):
        """Pipeline should handle large content files."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        # 10KB content file
        large_content = "Python programming. " * 500
        (docs / "large.txt").write_text(large_content)

        runner = PipelineRunner(data_dir=data_dir)
        stats = runner.run_from_files([str(docs / "large.txt")])
        runner.close()

        assert stats.pages_indexed == 1

    def test_pipeline_duplicate_files(self, tmp_path):
        """Pipeline should handle duplicate file paths."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.txt").write_text(
            "An article about testing and quality assurance."
        )

        runner = PipelineRunner(data_dir=data_dir)
        stats = runner.run_from_files([
            str(docs / "article.txt"),
            str(docs / "article.txt"),  # Duplicate
        ])
        runner.close()

        # Should handle duplicates gracefully
        assert stats.pages_crawled == 2

    def test_pipeline_mixed_formats(self, tmp_path):
        """Pipeline should handle mixed file formats."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.txt").write_text("Plain text article about programming.")
        (docs / "article.md").write_text("# Markdown Article

About software.")
        (docs / "article.html").write_text(
            "<html><body><p>HTML article about web development.</p></body></html>"
        )
        (docs / "article.json").write_text(
            '{"title": "JSON Article", "content": "About data formats."}'
        )

        runner = PipelineRunner(data_dir=data_dir)
        stats = runner.run_from_files([
            str(docs / "article.txt"),
            str(docs / "article.md"),
            str(docs / "article.html"),
            str(docs / "article.json"),
        ])
        runner.close()

        assert stats.pages_crawled == 4


class TestPipelineEdgeCases:
    """Test pipeline edge cases."""

    def test_pipeline_empty_directory(self, tmp_path):
        """Pipeline should handle empty file list."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        runner = PipelineRunner(data_dir=data_dir)
        stats = runner.run_from_files([])
        runner.close()

        assert stats.pages_crawled == 0
        assert stats.pages_indexed == 0

    def test_pipeline_all_filtered_out(self, tmp_path):
        """Pipeline should handle all content being filtered out."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "short1.txt").write_text("Hi")
        (docs / "short2.txt").write_text("Bye")

        runner = PipelineRunner(
            data_dir=data_dir,
            pipeline_config=PipelineConfig(min_content_length=100)
        )
        stats = runner.run_from_files([
            str(docs / "short1.txt"),
            str(docs / "short2.txt"),
        ])
        runner.close()

        assert stats.pages_filtered_in == 0
        assert stats.pages_filtered_out == 2
        assert stats.pages_indexed == 0

    def test_pipeline_with_special_filenames(self, tmp_path):
        """Pipeline should handle files with special characters in names."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article-with-dashes.txt").write_text(
            "Article with dashes in filename about programming."
        )
        (docs / "article_with_underscores.txt").write_text(
            "Article with underscores about software."
        )

        runner = PipelineRunner(data_dir=data_dir)
        stats = runner.run_from_files([
            str(docs / "article-with-dashes.txt"),
            str(docs / "article_with_underscores.txt"),
        ])
        runner.close()

        assert stats.pages_indexed == 2

    def test_pipeline_unicode_content(self, tmp_path):
        """Pipeline should handle unicode content."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "unicode.txt").write_text(
            "Unicode content: café, naïve, résumé, 日本語, العربية. "
            "International characters should be handled correctly."
        )

        runner = PipelineRunner(data_dir=data_dir)
        stats = runner.run_from_files([str(docs / "unicode.txt")])
        runner.close()

        assert stats.pages_indexed == 1

    def test_pipeline_multiple_interests(self, tmp_path):
        """Pipeline should match multiple interests."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        interest_store = InterestStore(
            store_path=os.path.join(data_dir, "interests.json")
        )
        interest_store.add(Interest(name="python", keywords=["python"]))
        interest_store.add(Interest(name="js", keywords=["javascript"]))
        interest_store.add(Interest(name="rust", keywords=["rust"]))

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "polyglot.txt").write_text(
            "Python, JavaScript, and Rust are all great programming languages."
        )

        runner = PipelineRunner(data_dir=data_dir)
        stats = runner.run_from_files([str(docs / "polyglot.txt")])
        runner.close()

        assert stats.interests_matched > 0
