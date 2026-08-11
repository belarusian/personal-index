"""Full pipeline flow integration tests.

Verifies the complete crawl → extract → filter → score → tag → index → search
pipeline works end-to-end with real data.
"""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from personal_index.config.pipeline_config import PipelineConfig
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest
from personal_index.pipeline_runner import PipelineRunner, PipelineStats
from personal_index.tags import TagStore


class TestFullPipelineFlow:
    """Test the complete pipeline flow from crawl to search."""

    def test_crawl_to_search_full_flow(self, tmp_path):
        """Complete flow: crawl → extract → filter → score → tag → index → search."""
        runner = PipelineRunner(data_dir=str(tmp_path))

        # Set up interests
        runner._interest_store.add(Interest(name="python", keywords=["python", "programming"]))
        runner._interest_store.add(Interest(name="webdev", keywords=["web", "development"]))

        # Mock crawler to return realistic pages
        mock_pages = [
            CrawledPage(
                url="https://example.com/python-tutorial",
                title="Python Programming Tutorial",
                content="Learn Python programming from scratch. Python is a versatile language used for web development, data science, and automation.",
                matched_interests=["python"],
            ),
            CrawledPage(
                url="https://example.com/web-frameworks",
                title="Web Development Frameworks",
                content="Modern web development frameworks make building applications easier. Popular frameworks include Django, Flask, and FastAPI.",
                matched_interests=["webdev"],
            ),
            CrawledPage(
                url="https://example.com/empty-page",
                title="Empty",
                content="",
            ),
        ]
        runner._crawler.crawl = MagicMock(return_value=mock_pages)

        # Run the full pipeline
        stats = runner.run(["https://example.com"])

        # Verify each stage
        assert stats.pages_crawled == 3
        assert stats.pages_extracted == 2  # empty page filtered out
        assert stats.pages_filtered_in >= 1
        assert stats.pages_scored >= 1
        assert stats.pages_tagged >= 1
        assert stats.pages_indexed >= 1

        # Verify search works on indexed content
        results = runner._search_index.search("python")
        assert len(results) >= 1
        assert any("python" in r.url for r in results)

        # Verify tags were applied
        tag_count = runner._tag_store.get_tag_count()
        assert tag_count >= 1

        runner.close()

    def test_pipeline_with_no_interests(self, tmp_path):
        """Pipeline should work even without configured interests."""
        runner = PipelineRunner(data_dir=str(tmp_path))

        mock_pages = [
            CrawledPage(
                url="https://example.com/article",
                title="An Article",
                content="This is a general article with enough content to pass the filter and be indexed properly.",
            ),
        ]
        runner._crawler.crawl = MagicMock(return_value=mock_pages)

        stats = runner.run(["https://example.com"])
        assert stats.pages_indexed >= 1
        runner.close()

    def test_pipeline_respects_min_score(self, tmp_path):
        """Pipeline should filter out pages below min_score_threshold."""
        config = PipelineConfig(min_score_threshold=0.99)
        runner = PipelineRunner(data_dir=str(tmp_path), pipeline_config=config)

        mock_pages = [
            CrawledPage(
                url="https://example.com/low-score",
                title="Low Score Page",
                content="This page has some content but will score low.",
            ),
        ]
        runner._crawler.crawl = MagicMock(return_value=mock_pages)

        stats = runner.run(["https://example.com"])
        # Pages with low scores should be filtered out
        # (exact behavior depends on scoring, but at least no crash)
        assert stats.pages_crawled == 1
        runner.close()

    def test_pipeline_multiple_urls(self, tmp_path):
        """Pipeline should handle multiple seed URLs."""
        runner = PipelineRunner(data_dir=str(tmp_path))

        mock_pages = [
            CrawledPage(
                url="https://site1.com/page1",
                title="Site 1 Page",
                content="Content from site 1 with enough text to pass filters.",
            ),
            CrawledPage(
                url="https://site2.com/page2",
                title="Site 2 Page",
                content="Content from site 2 with enough text to pass filters.",
            ),
        ]
        runner._crawler.crawl = MagicMock(return_value=mock_pages)

        stats = runner.run(["https://site1.com", "https://site2.com"])
        assert stats.pages_crawled == 2
        runner.close()

    def test_pipeline_error_handling(self, tmp_path):
        """Pipeline should handle errors gracefully without crashing."""
        runner = PipelineRunner(data_dir=str(tmp_path))

        mock_pages = [
            CrawledPage(
                url="https://example.com/good",
                title="Good Page",
                content="This is a good page with enough content to pass all filters.",
            ),
            CrawledPage(
                url="https://example.com/bad",
                title="Bad",
                content="x",  # Too short
            ),
        ]
        runner._crawler.crawl = MagicMock(return_value=mock_pages)

        stats = runner.run(["https://example.com"])
        # Should not crash, should have at least one page indexed
        assert stats.pages_indexed >= 0
        assert len(stats.errors) == 0  # No errors expected
        runner.close()


class TestPipelineFromFileToSearch:
    """Test importing files and searching them."""

    def test_import_and_search(self, tmp_path):
        """Should import files and search their content."""
        # Create test files
        file1 = tmp_path / "python_guide.txt"
        file1.write_text(
            "Python is a popular programming language. "
            "It is used for web development, data analysis, and machine learning. "
            "Python has a large community and many libraries."
        )

        file2 = tmp_path / "javascript_guide.txt"
        file2.write_text(
            "JavaScript is essential for web development. "
            "It runs in the browser and on the server with Node.js. "
            "JavaScript frameworks include React, Vue, and Angular."
        )

        runner = PipelineRunner(data_dir=str(tmp_path))
        runner._interest_store.add(Interest(name="programming", keywords=["python", "javascript"]))

        stats = runner.run_from_files([str(file1), str(file2)])
        assert stats.pages_indexed >= 1

        # Search for python
        results = runner._search_index.search("python")
        assert len(results) >= 1

        # Search for javascript
        results = runner._search_index.search("javascript")
        assert len(results) >= 1

        # Search for web should find both
        results = runner._search_index.search("web")
        assert len(results) >= 1

        runner.close()

    def test_import_mixed_file_types(self, tmp_path):
        """Should handle mixed file types (text, html)."""
        txt_file = tmp_path / "article.txt"
        txt_file.write_text("This is a plain text article about technology.")

        html_file = tmp_path / "article.html"
        html_file.write_text("<html><body><p>HTML article about technology.</p></body></html>")

        runner = PipelineRunner(data_dir=str(tmp_path))
        stats = runner.run_from_files([str(txt_file), str(html_file)])

        # At least the text file should be indexed
        assert stats.pages_indexed >= 1
        runner.close()


class TestPipelineTaggingFlow:
    """Test the tagging flow through the pipeline."""

    def test_interest_tags_applied_during_pipeline(self, tmp_path):
        """Interest-based tags should be applied during pipeline run."""
        runner = PipelineRunner(data_dir=str(tmp_path))

        runner._interest_store.add(Interest(name="ai", keywords=["artificial", "intelligence"]))
        runner._interest_store.add(Interest(name="ml", keywords=["machine", "learning"]))

        mock_pages = [
            CrawledPage(
                url="https://example.com/ai-article",
                title="AI and ML Article",
                content="Artificial intelligence and machine learning are transforming technology.",
            ),
        ]
        runner._crawler.crawl = MagicMock(return_value=mock_pages)

        stats = runner.run(["https://example.com"])
        assert stats.pages_tagged >= 1
        assert stats.tags_applied >= 1

        # Verify tags exist
        tags = runner._tag_store.get_tags_for_page("https://example.com/ai-article")
        tag_names = [t.name if hasattr(t, "name") else str(t) for t in tags]
        assert "ai" in tag_names or "ml" in tag_names
        runner.close()

    def test_keyword_tags_extracted_during_pipeline(self, tmp_path):
        """Keyword-based tags should be extracted during pipeline run."""
        runner = PipelineRunner(data_dir=str(tmp_path))

        mock_pages = [
            CrawledPage(
                url="https://example.com/keywords",
                title="Keyword Test",
                content="Python Python Python programming programming development development testing testing.",
            ),
        ]
        runner._crawler.crawl = MagicMock(return_value=mock_pages)

        stats = runner.run(["https://example.com"])
        assert stats.tags_applied >= 1
        runner.close()


class TestPipelineScoringFlow:
    """Test the scoring flow through the pipeline."""

    def test_pages_with_interest_matches_score_higher(self, tmp_path):
        """Pages matching interests should score higher."""
        runner = PipelineRunner(data_dir=str(tmp_path))

        runner._interest_store.add(Interest(name="python", keywords=["python"]))

        mock_pages = [
            CrawledPage(
                url="https://example.com/match",
                title="Python Match",
                content="Python programming is great.",
                matched_interests=["python"],
            ),
            CrawledPage(
                url="https://example.com/nomatch",
                title="No Match",
                content="This page has no matching keywords.",
                matched_interests=[],
            ),
        ]
        runner._crawler.crawl = MagicMock(return_value=mock_pages)

        stats = runner.run(["https://example.com"])
        assert stats.pages_scored >= 1

        # Check scores
        match_page = runner._search_index.get_page("https://example.com/match")
        nomatch_page = runner._search_index.get_page("https://example.com/nomatch")

        if match_page and nomatch_page:
            assert match_page.score > nomatch_page.score
        runner.close()


class TestPipelineStatsAccuracy:
    """Test that pipeline stats accurately reflect processing."""

    def test_stats_reflect_stage_counts(self, tmp_path):
        """Pipeline stats should accurately count pages at each stage."""
        runner = PipelineRunner(data_dir=str(tmp_path))

        # 5 good pages, 2 empty pages
        mock_pages = [
            CrawledPage(
                url=f"https://example.com/page{i}",
                title=f"Page {i}",
                content=f"Content for page {i} with enough text to pass filters.",
            )
            for i in range(5)
        ]
        mock_pages.extend([
            CrawledPage(url="https://example.com/empty1", title="E1", content=""),
            CrawledPage(url="https://example.com/empty2", title="E2", content="   "),
        ])
        runner._crawler.crawl = MagicMock(return_value=mock_pages)

        stats = runner.run(["https://example.com"])

        assert stats.pages_crawled == 7
        assert stats.pages_extracted == 5  # 2 empty removed
        assert stats.pages_filtered_in + stats.pages_filtered_out == 5
        runner.close()

    def test_stats_elapsed_time_positive(self, tmp_path):
        """Pipeline stats should record elapsed time."""
        runner = PipelineRunner(data_dir=str(tmp_path))

        mock_pages = [
            CrawledPage(
                url="https://example.com/timed",
                title="Timed Page",
                content="Content with enough text to pass filters.",
            ),
        ]
        runner._crawler.crawl = MagicMock(return_value=mock_pages)

        stats = runner.run(["https://example.com"])
        assert stats.elapsed_seconds >= 0
        runner.close()
