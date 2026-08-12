"""Tests for cli_top.py — top_pages command."""

from __future__ import annotations

import json
import os

from click.testing import CliRunner

from personal_index.cli_top import top_pages
from personal_index.index import SearchIndex
from personal_index.models import CrawledPage


class TestTopPagesNoData:
    """Tests when there are no indexed pages."""

    def test_no_pages_message(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(top_pages, ["--data-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "No indexed pages found" in result.output


class TestTopPagesTextFormat:
    """Tests for text output format."""

    def test_shows_ranked_pages(self, tmp_path):
        runner = CliRunner()
        db_path = os.path.join(str(tmp_path), "search_index.json")

        # Seed the index with pages of different scores
        index = SearchIndex(db_path=db_path)
        index.add_page(CrawledPage(
            url="http://example.com/a",
            title="High Score Page",
            content="python programming test",
        ))
        index._pages["http://example.com/a"].score = 0.9
        index.add_page(CrawledPage(
            url="http://example.com/b",
            title="Low Score Page",
            content="random stuff",
        ))
        index._pages["http://example.com/b"].score = 0.3
        index._save()

        result = runner.invoke(top_pages, ["--data-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "High Score Page" in result.output
        assert "Low Score Page" in result.output
        # Higher score should appear first
        assert result.output.index("High Score Page") < result.output.index("Low Score Page")

    def test_limit_option(self, tmp_path):
        runner = CliRunner()
        db_path = os.path.join(str(tmp_path), "search_index.json")

        index = SearchIndex(db_path=db_path)
        for i in range(5):
            index.add_page(CrawledPage(
                url=f"http://example.com/page{i}",
                title=f"Page {i}",
                content=f"content {i}",
            ))
            index._pages[f"http://example.com/page{i}"].score = float(i)
        index._save()

        result = runner.invoke(top_pages, ["--data-dir", str(tmp_path), "--limit", "2"])
        assert result.exit_code == 0
        # Should only show 2 pages
        assert "Page 4" in result.output
        assert "Page 3" in result.output
        assert "Page 2" not in result.output


class TestTopPagesJsonFormat:
    """Tests for JSON output format."""

    def test_json_output_structure(self, tmp_path):
        runner = CliRunner()
        db_path = os.path.join(str(tmp_path), "search_index.json")

        index = SearchIndex(db_path=db_path)
        index.add_page(CrawledPage(
            url="http://example.com/a",
            title="Test Page",
            content="python test",
        ))
        index._pages["http://example.com/a"].score = 0.75
        index._save()

        result = runner.invoke(top_pages, ["--data-dir", str(tmp_path), "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "top_pages" in data
        assert "total" in data
        assert len(data["top_pages"]) == 1
        page = data["top_pages"][0]
        assert page["rank"] == 1
        assert page["url"] == "http://example.com/a"
        assert page["title"] == "Test Page"
        assert abs(page["score"] - 0.75) < 0.001
