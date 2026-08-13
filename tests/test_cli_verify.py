"""Tests for cli_verify.py — verify command."""

from __future__ import annotations

import os

from click.testing import CliRunner

from personal_index.cli_verify import verify


class TestVerifyQuick:
    """Tests for quick verification mode."""

    def test_quick_verify_passes(self, tmp_path):
        """Quick verify should pass all component checks."""
        runner = CliRunner()
        result = runner.invoke(verify, ["--data-dir", str(tmp_path), "--quick"])
        assert result.exit_code == 0
        assert "All checks passed" in result.output
        assert "Data directory is writable" in result.output
        assert "Interest store works" in result.output
        assert "Tag store works" in result.output
        assert "Search index works" in result.output
        assert "Content filter works" in result.output
        assert "Content scorer works" in result.output

    def test_quick_verify_skips_pipeline(self, tmp_path):
        """Quick mode should skip the full pipeline test."""
        runner = CliRunner()
        result = runner.invoke(verify, ["--data-dir", str(tmp_path), "--quick"])
        assert result.exit_code == 0
        assert "Running full pipeline self-test" not in result.output

    def test_quick_verify_cleanup(self, tmp_path):
        """Verify should clean up temporary verify files."""
        runner = CliRunner()
        result = runner.invoke(verify, ["--data-dir", str(tmp_path), "--quick"])
        assert result.exit_code == 0
        # Verify temp files should be cleaned up
        assert not os.path.exists(os.path.join(str(tmp_path), "verify_interests.json"))
        assert not os.path.exists(os.path.join(str(tmp_path), "verify_tags.json"))
        assert not os.path.exists(os.path.join(str(tmp_path), "verify_index.json"))


class TestVerifyFull:
    """Tests for full verification mode."""

    def test_full_verify_passes(self, tmp_path):
        """Full verify should pass all checks including pipeline test."""
        runner = CliRunner()
        result = runner.invoke(verify, ["--data-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "All checks passed" in result.output
        assert "Running full pipeline self-test" in result.output
        assert "Full pipeline: all stages" in result.output

    def test_full_verify_pipeline_cleanup(self, tmp_path):
        """Full verify should clean up pipeline test directory."""
        runner = CliRunner()
        result = runner.invoke(verify, ["--data-dir", str(tmp_path)])
        assert result.exit_code == 0
        # Pipeline test directory should be cleaned up
        assert not os.path.exists(os.path.join(str(tmp_path), ".verify_pipeline"))

    def test_full_verify_shows_check_count(self, tmp_path):
        """Verify should show the number of checks passed."""
        runner = CliRunner()
        result = runner.invoke(verify, ["--data-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "checks passed" in result.output


class TestPipelineHelpers:
    """Tests for the extracted _check_full_pipeline helper functions."""

    def test_create_test_page(self, tmp_path):
        """_create_test_page reads file and returns CrawledPage."""
        from personal_index.cli_verify import _create_test_content, _create_test_page

        test_data_dir, _ = _create_test_content(str(tmp_path))
        page = _create_test_page(test_data_dir)
        assert page.title == "Python Overview"
        assert "Python" in page.content
        assert page.url.endswith("test_article.txt")

    def test_run_filter_passes(self, tmp_path):
        """_run_filter returns True for valid content."""
        from personal_index.cli_verify import _run_filter
        from personal_index.content_filter import ContentFilter, FilterConfig
        from personal_index.models import CrawledPage

        f = ContentFilter(config=FilterConfig(min_content_length=10, min_title_length=1))
        page = CrawledPage(url="http://x.com", title="T", content="This is enough content")
        passed, msg = _run_filter(f, page)
        assert passed is True
        assert msg == ""

    def test_run_filter_fails(self, tmp_path):
        """_run_filter returns False for short content."""
        from personal_index.cli_verify import _run_filter
        from personal_index.content_filter import ContentFilter, FilterConfig
        from personal_index.models import CrawledPage

        f = ContentFilter(config=FilterConfig(min_content_length=100, min_title_length=1))
        page = CrawledPage(url="http://x.com", title="T", content="short")
        passed, msg = _run_filter(f, page)
        assert passed is False
        assert "filtered out" in msg

    def test_run_score_sets_relevance(self, tmp_path):
        """_run_score sets page.relevance_score and returns it."""
        from personal_index.cli_verify import _run_score
        from personal_index.content_scoring import ContentScorer, ScoreWeights
        from personal_index.models import CrawledPage

        scorer = ContentScorer(weights=ScoreWeights())
        page = CrawledPage(url="http://x.com", title="T", content="hello world")
        score = _run_score(scorer, page, page.content)
        assert score > 0
        assert page.relevance_score == score

    def test_run_tag_index(self, tmp_path):
        """_run_tag_index tags, indexes, and returns search results."""
        from personal_index.cli_verify import _run_tag_index
        from personal_index.index import SearchIndex
        from personal_index.models import CrawledPage
        from personal_index.tags import TagStore

        tag_store = TagStore(store_path=str(tmp_path / "tags.json"))
        search_index = SearchIndex(db_path=str(tmp_path / "index.json"))
        page = CrawledPage(url="http://x.com", title="Python", content="python programming")
        results = _run_tag_index(tag_store, search_index, page)
        assert len(results) > 0
