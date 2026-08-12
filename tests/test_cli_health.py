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
