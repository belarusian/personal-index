"""Tests for dedup CLI command."""

from __future__ import annotations

import os
import pytest

from click.testing import CliRunner

from personal_index.cli import main
from personal_index.index import SearchIndex
from personal_index.models import IndexedPage


class TestDedupCLI:
    def test_dedup_command_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert "dedup" in result.output

    def test_dedup_no_content(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--data-dir", str(tmp_path), "dedup"],
        )
        assert "No indexed content found" in result.output or result.exit_code == 0

    def test_dedup_with_duplicates(self, tmp_path):
        dd = str(tmp_path)
        os.makedirs(dd, exist_ok=True)

        idx_path = os.path.join(dd, "search_index.json")
        idx = SearchIndex(db_path=idx_path)

        # Add duplicate content
        idx.add_page(IndexedPage(
            url="https://a.com",
            title="Page A",
            content="This is the exact same content",
            score=8.0,
        ))
        idx.add_page(IndexedPage(
            url="https://b.com",
            title="Page B",
            content="This is the exact same content",
            score=7.0,
        ))
        idx.add_page(IndexedPage(
            url="https://c.com",
            title="Page C",
            content="Different content here",
            score=6.0,
        ))
        idx._save()

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--data-dir", dd, "dedup", "--dry-run"],
        )
        assert result.exit_code == 0
        assert "Duplicates found: 1" in result.output

    def test_dedup_method_option(self, tmp_path):
        dd = str(tmp_path)
        os.makedirs(dd, exist_ok=True)

        idx_path = os.path.join(dd, "search_index.json")
        idx = SearchIndex(db_path=idx_path)

        idx.add_page(IndexedPage(
            url="https://example.com/",
            title="Page A",
            content="Content A",
            score=8.0,
        ))
        idx.add_page(IndexedPage(
            url="https://example.com",
            title="Page B",
            content="Content B",
            score=7.0,
        ))
        idx._save()

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--data-dir", dd, "dedup", "--method", "url"],
        )
        assert result.exit_code == 0
