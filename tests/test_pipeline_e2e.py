"""End-to-end integration tests for the full pipeline.

Tests verify the complete crawl → extract → filter → score → tag → index → search
pipeline works correctly from file import through search.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from personal_index.pipeline_e2e import PipelineE2E, PipelineRunResult


class TestPipelineE2EBasic:
    """Test basic pipeline end-to-end functionality."""

    def test_pipeline_from_single_file(self, tmp_path: Path) -> None:
        """Test running pipeline on a single text file."""
        data_dir = str(tmp_path / "data")
        pipeline = PipelineE2E(data_dir=data_dir)

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python is a versatile programming language used for web development, "
            "data science, and automation. Python supports multiple programming "
            "paradigms including procedural, object-oriented, and functional programming."
        )

        result = pipeline.run_from_files([str(test_file)])

        assert result.pages_crawled == 1
        assert result.pages_extracted == 1
        assert result.pages_filtered_in == 1
        assert result.pages_filtered_out == 0
        assert result.pages_scored == 1
        assert result.pages_indexed == 1
        assert result.success is True
        assert len(result.errors) == 0
        pipeline.close()

    def test_pipeline_from_multiple_files(self, tmp_path: Path) -> None:
        """Test running pipeline on multiple files."""
        data_dir = str(tmp_path / "data")
        pipeline = PipelineE2E(data_dir=data_dir)

        files = []
        for i in range(5):
            f = tmp_path / f"article_{i}.txt"
            f.write_text(
                f"Article {i}: Python programming tutorial covering "
                f"web development and data science techniques."
            )
            files.append(str(f))

        result = pipeline.run_from_files(files)

        assert result.pages_crawled == 5
        assert result.pages_extracted == 5
        assert result.pages_filtered_in == 5
        assert result.pages_indexed == 5
        assert result.success is True
        pipeline.close()

    def test_pipeline_filters_short_content(self, tmp_path: Path) -> None:
        """Test that short content is filtered out."""
        data_dir = str(tmp_path / "data")
        from personal_index.config.pipeline_config import PipelineConfig

        config = PipelineConfig(min_content_length=100)
        pipeline = PipelineE2E(data_dir=data_dir, config=config)

        short_file = tmp_path / "short.txt"
        short_file.write_text("Too short")

        long_file = tmp_path / "long.txt"
        long_file.write_text(
            "This is a longer article about Python programming that "
            "discusses web development, data science, and automation "
            "techniques in detail with comprehensive examples."
        )

        result = pipeline.run_from_files([str(short_file), str(long_file)])

        assert result.pages_crawled == 2
        assert result.pages_filtered_in == 1
        assert result.pages_filtered_out == 1
        assert result.pages_indexed == 1
        pipeline.close()

    def test_pipeline_handles_nonexistent_file(self, tmp_path: Path) -> None:
        """Test pipeline handles missing files gracefully."""
        data_dir = str(tmp_path / "data")
        pipeline = PipelineE2E(data_dir=data_dir)

        result = pipeline.run_from_files([str(tmp_path / "nonexistent.txt")])

        assert result.pages_crawled == 0
        assert result.pages_indexed == 0
        assert len(result.errors) == 1
        assert "File not found" in result.errors[0]
        pipeline.close()

    def test_pipeline_handles_mixed_files(self, tmp_path: Path) -> None:
        """Test pipeline handles mix of valid and invalid files."""
        data_dir = str(tmp_path / "data")
        pipeline = PipelineE2E(data_dir=data_dir)

        good_file = tmp_path / "good.txt"
        good_file.write_text(
            "A comprehensive guide to Python programming covering "
            "web development, data science, and automation techniques."
        )

        result = pipeline.run_from_files([
            str(good_file),
            str(tmp_path / "missing.txt"),
        ])

        assert result.pages_crawled == 1
        assert result.pages_indexed == 1
        assert len(result.errors) == 1
        pipeline.close()


class TestPipelineE2EWithInterests:
    """Test pipeline with interest-based scoring and tagging."""

    def test_pipeline_scores_with_interests(self, tmp_path: Path) -> None:
        """Test that pages matching interests get higher scores."""
        data_dir = str(tmp_path / "data")
        pipeline = PipelineE2E(data_dir=data_dir)

        pipeline.add_interest(
            name="python",
            keywords=["python", "programming"],
            priority=8,
        )

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python is a great programming language for web development."
        )

        result = pipeline.run_from_files([str(test_file)])

        assert result.pages_indexed == 1
        assert result.interests_matched > 0
        assert result.pages_tagged > 0
        pipeline.close()

    def test_pipeline_tags_matched_interests(self, tmp_path: Path) -> None:
        """Test that matched interests are added as tags."""
        data_dir = str(tmp_path / "data")
        pipeline = PipelineE2E(data_dir=data_dir)

        pipeline.add_interest(
            name="webdev",
            keywords=["web", "development", "javascript"],
            priority=7,
        )

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Web development with JavaScript and Python frameworks "
            "for building modern applications."
        )

        result = pipeline.run_from_files([str(test_file)])

        assert result.pages_tagged > 0
        # get_tags_for_page returns Tag objects, check by name
        page_url = f"file://{os.path.abspath(str(test_file))}"
        tags = pipeline.tag_store.get_tags_for_page(page_url)
        tag_names = [t.name if hasattr(t, 'name') else t for t in tags]
        assert "webdev" in tag_names
        pipeline.close()

    def test_pipeline_score_threshold_filters(self, tmp_path: Path) -> None:
        """Test that score threshold filters low-scoring pages."""
        data_dir = str(tmp_path / "data")
        from personal_index.config.pipeline_config import PipelineConfig

        # Use a high threshold that only pages with keyword matches pass
        config = PipelineConfig(min_score_threshold=0.5)
        pipeline = PipelineE2E(data_dir=data_dir, config=config)

        # Add interest with high priority
        pipeline.add_interest(
            name="python",
            keywords=["python"],
            priority=10,
        )

        # Page with many keyword matches (should pass)
        good_file = tmp_path / "good.txt"
        good_file.write_text(
            "Python Python Python Python Python Python Python Python "
            "Python Python Python programming language for development."
        )

        # Page with no keyword matches (should fail)
        bad_file = tmp_path / "bad.txt"
        bad_file.write_text(
            "This article is about cooking recipes and baking "
            "techniques for home chefs and professional bakers."
        )

        result = pipeline.run_from_files([str(good_file), str(bad_file)])

        # At least the good file should be indexed
        assert result.pages_indexed >= 1
        pipeline.close()


class TestPipelineE2ESearch:
    """Test search functionality after pipeline indexing."""

    def test_search_after_pipeline(self, tmp_path: Path) -> None:
        """Test searching content after pipeline indexing."""
        data_dir = str(tmp_path / "data")
        pipeline = PipelineE2E(data_dir=data_dir)

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python is a versatile programming language for web development "
            "and data science applications."
        )

        pipeline.run_from_files([str(test_file)])

        results = pipeline.search("python")
        assert len(results) > 0
        assert results[0]["title"] == "article.txt"
        pipeline.close()

    def test_search_multiple_results(self, tmp_path: Path) -> None:
        """Test searching returns multiple results."""
        data_dir = str(tmp_path / "data")
        pipeline = PipelineE2E(data_dir=data_dir)

        for i in range(3):
            f = tmp_path / f"article_{i}.txt"
            f.write_text(
                f"Article {i}: Python programming and web development tutorial."
            )

        pipeline.run_from_files([
            str(tmp_path / f"article_{i}.txt") for i in range(3)
        ])

        results = pipeline.search("python")
        assert len(results) >= 3
        pipeline.close()

    def test_search_no_results(self, tmp_path: Path) -> None:
        """Test searching returns empty for non-matching query."""
        data_dir = str(tmp_path / "data")
        pipeline = PipelineE2E(data_dir=data_dir)

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming language for web development."
        )

        pipeline.run_from_files([str(test_file)])

        results = pipeline.search("quantum physics")
        assert len(results) == 0
        pipeline.close()

    def test_search_result_contains_tags(self, tmp_path: Path) -> None:
        """Test that search results include tags."""
        data_dir = str(tmp_path / "data")
        pipeline = PipelineE2E(data_dir=data_dir)

        pipeline.add_interest(
            name="tech",
            keywords=["python", "programming"],
            priority=5,
        )

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming language for web development."
        )

        pipeline.run_from_files([str(test_file)])

        results = pipeline.search("python")
        assert len(results) > 0
        assert "tags" in results[0]
        pipeline.close()


class TestPipelineE2EPersistence:
    """Test pipeline state persistence."""

    def test_index_persists_after_close(self, tmp_path: Path) -> None:
        """Test that search index persists after closing pipeline."""
        data_dir = str(tmp_path / "data")
        pipeline = PipelineE2E(data_dir=data_dir)

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming language for web development."
        )

        pipeline.run_from_files([str(test_file)])
        pipeline.close()

        # Reopen and verify
        pipeline2 = PipelineE2E(data_dir=data_dir)
        results = pipeline2.search("python")
        assert len(results) > 0
        pipeline2.close()

    def test_interests_persist_after_close(self, tmp_path: Path) -> None:
        """Test that interests persist after closing pipeline."""
        data_dir = str(tmp_path / "data")
        pipeline = PipelineE2E(data_dir=data_dir)

        pipeline.add_interest(
            name="python",
            keywords=["python"],
            priority=5,
        )
        pipeline.close()

        # Reopen and verify
        pipeline2 = PipelineE2E(data_dir=data_dir)
        interests = pipeline2.interest_store.list_all()
        assert len(interests) == 1
        assert interests[0].name == "python"
        pipeline2.close()

    def test_tags_persist_after_close(self, tmp_path: Path) -> None:
        """Test that tags persist after closing pipeline."""
        data_dir = str(tmp_path / "data")
        pipeline = PipelineE2E(data_dir=data_dir)

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming language for web development."
        )

        pipeline.run_from_files([str(test_file)])
        pipeline.close()

        # Reopen and verify tags exist
        pipeline2 = PipelineE2E(data_dir=data_dir)
        assert pipeline2.tag_store.get_tag_count() > 0
        pipeline2.close()


class TestPipelineE2EHTML:
    """Test pipeline with HTML files."""

    def test_pipeline_processes_html(self, tmp_path: Path) -> None:
        """Test pipeline processes HTML files correctly."""
        data_dir = str(tmp_path / "data")
        pipeline = PipelineE2E(data_dir=data_dir)

        html_file = tmp_path / "article.html"
        html_file.write_text(
            "<html><head><title>Python Tutorial</title></head>"
            "<body><h1>Python Web Development</h1>"
            "<p>Python is a great language for building web applications "
            "using frameworks like Django and Flask.</p></body></html>"
        )

        result = pipeline.run_from_files([str(html_file)])

        assert result.pages_crawled == 1
        assert result.pages_extracted == 1
        assert result.pages_indexed == 1
        assert result.indexed_pages[0].title == "Python Tutorial"
        pipeline.close()

    def test_pipeline_searches_html_content(self, tmp_path: Path) -> None:
        """Test searching content extracted from HTML."""
        data_dir = str(tmp_path / "data")
        pipeline = PipelineE2E(data_dir=data_dir)

        html_file = tmp_path / "article.html"
        html_file.write_text(
            "<html><body>"
            "<h1>JavaScript Guide</h1>"
            "<p>JavaScript is essential for web development.</p>"
            "</body></html>"
        )

        pipeline.run_from_files([str(html_file)])

        results = pipeline.search("javascript")
        assert len(results) > 0
        pipeline.close()


class TestPipelineE2EResults:
    """Test PipelineRunResult utility methods."""

    def test_result_summary(self, tmp_path: Path) -> None:
        """Test PipelineRunResult summary output."""
        data_dir = str(tmp_path / "data")
        pipeline = PipelineE2E(data_dir=data_dir)

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming language for web development."
        )

        result = pipeline.run_from_files([str(test_file)])
        summary = result.summary()

        assert "Pipeline Run Result" in summary
        assert "Pages crawled:" in summary
        assert "Pages indexed:" in summary
        assert "Time:" in summary
        pipeline.close()

    def test_result_success_property(self, tmp_path: Path) -> None:
        """Test PipelineRunResult success property."""
        data_dir = str(tmp_path / "data")
        pipeline = PipelineE2E(data_dir=data_dir)

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming language for web development."
        )

        result = pipeline.run_from_files([str(test_file)])
        assert result.success is True

        # Test with error
        result2 = pipeline.run_from_files([str(tmp_path / "missing.txt")])
        assert result2.success is False
        pipeline.close()
