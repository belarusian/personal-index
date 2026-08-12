"""Tests for recommend CLI command."""

from __future__ import annotations

import pytest

from click.testing import CliRunner

from personal_index.cli import main
from personal_index.content_recommender import ContentItem, Recommender


class TestRecommendCLI:
    def test_recommend_command_exists(self):
        """Verify the recommend command is registered."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert "recommend" in result.output

    def test_recommend_no_content(self, tmp_path):
        """Test recommend with no indexed content."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--data-dir", str(tmp_path), "recommend", "python"],
        )
        assert "No indexed content found" in result.output or result.exit_code == 0

    def test_recommend_with_content(self, tmp_path):
        """Test recommend with indexed content."""
        import os
        import json

        dd = str(tmp_path)
        os.makedirs(dd, exist_ok=True)

        # Create a search index with some pages
        from personal_index.index import SearchIndex
        from personal_index.models import IndexedPage

        idx_path = os.path.join(dd, "search_index.json")
        idx = SearchIndex(db_path=idx_path)

        idx.add_page(IndexedPage(
            url="https://example.com/python",
            title="Python Tutorial",
            content="Learn Python programming",
            score=8.0,
        ))
        idx.add_page(IndexedPage(
            url="https://example.com/javascript",
            title="JavaScript Guide",
            content="Learn JavaScript web development",
            score=7.0,
        ))
        idx._save()

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--data-dir", dd, "recommend", "python"],
        )
        assert result.exit_code == 0
        assert "Python Tutorial" in result.output

    def test_recommend_top_n(self, tmp_path):
        """Test recommend with custom top-n."""
        import os

        dd = str(tmp_path)
        os.makedirs(dd, exist_ok=True)

        from personal_index.index import SearchIndex
        from personal_index.models import IndexedPage

        idx_path = os.path.join(dd, "search_index.json")
        idx = SearchIndex(db_path=idx_path)

        for i in range(10):
            idx.add_page(IndexedPage(
                url=f"https://example.com/page{i}",
                title=f"Page {i} Python",
                content="Python content",
                score=float(i),
            ))
        idx._save()

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--data-dir", dd, "recommend", "python", "--top-n", "3"],
        )
        assert result.exit_code == 0
