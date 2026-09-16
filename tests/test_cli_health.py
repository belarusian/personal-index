"""Tests for health CLI command."""

from __future__ import annotations

import os

from click.testing import CliRunner

from personal_index.cli import main
from personal_index.index import SearchIndex
from personal_index.models import IndexedPage


class TestHealthCLI:
    def test_health_command_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert "health" in result.output

    def test_health_no_content(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--data-dir", str(tmp_path), "health"],
        )
        assert "No indexed content found" in result.output or result.exit_code == 0

    def test_health_with_content(self, tmp_path):
        dd = str(tmp_path)
        os.makedirs(dd, exist_ok=True)

        idx_path = os.path.join(dd, "search_index.json")
        idx = SearchIndex(db_path=idx_path)

        idx.add_page(IndexedPage(
            url="https://example.com/good",
            title="A Good Page About Python Programming",
            content="This is a comprehensive article about Python programming that covers many topics in detail.",
            score=8.0,
        ))
        idx._save()

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--data-dir", dd, "health"],
        )
        assert result.exit_code == 0
        assert "Content Health Report" in result.output

    def test_health_with_issues(self, tmp_path):
        dd = str(tmp_path)
        os.makedirs(dd, exist_ok=True)

        idx_path = os.path.join(dd, "search_index.json")
        idx = SearchIndex(db_path=idx_path)

        idx.add_page(IndexedPage(
            url="https://example.com/bad",
            title="",
            content="Short",
            score=0.0,
        ))
        idx._save()

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--data-dir", dd, "health"],
        )
        assert result.exit_code == 0
        assert "Issues Found" in result.output

    def _setup_page(self, dd, url, title, content, tag=None):
        idx = SearchIndex(db_path=os.path.join(dd, "search_index.json"))
        idx.add_page(IndexedPage(url=url, title=title, content=content, score=8.0))
        idx._save()
        if tag is not None:
            from personal_index.tags import TagStore
            ts = TagStore(store_path=os.path.join(dd, "tags.json"))
            ts.add_tag_to_page(url, tag)
        return idx

    def test_health_max_title_length_flags_long_title(self, tmp_path):
        dd = str(tmp_path)
        os.makedirs(dd, exist_ok=True)
        self._setup_page(dd, "https://example.com/long", "A" * 15, "x" * 60)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--data-dir", dd, "health", "--max-title-length", "10"],
        )
        assert result.exit_code == 0
        assert "Title exceeds 10 characters" in result.output

    def test_health_default_max_title_length_no_issue(self, tmp_path):
        dd = str(tmp_path)
        os.makedirs(dd, exist_ok=True)
        self._setup_page(dd, "https://example.com/long", "A" * 15, "x" * 60)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--data-dir", dd, "health"],
        )
        assert result.exit_code == 0
        assert "Title exceeds" not in result.output

    def test_health_min_tags_2_flags_single_tag(self, tmp_path):
        dd = str(tmp_path)
        os.makedirs(dd, exist_ok=True)
        self._setup_page(dd, "https://example.com/tagged", "A Good Page Title", "x" * 60, tag="python")
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--data-dir", dd, "health", "--require-tags", "--min-tags", "2"],
        )
        assert result.exit_code == 0
        assert "Content has no tags (min 2 required)" in result.output

    def test_health_default_min_tags_single_tag_no_issue(self, tmp_path):
        dd = str(tmp_path)
        os.makedirs(dd, exist_ok=True)
        self._setup_page(dd, "https://example.com/tagged", "A Good Page Title", "x" * 60, tag="python")
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--data-dir", dd, "health", "--require-tags"],
        )
        assert result.exit_code == 0
        assert "Content has no tags" not in result.output
