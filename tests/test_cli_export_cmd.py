"""Pinning tests for the REACHABLE `personal-index export` command (ARCH-98, Option A).

The reachable `export` is `cli_export.export_cmd`, wired onto the `main` group
in cli.py. These tests invoke it end-to-end via click CliRunner against
`cli.main` (not the private helpers) and pin the Option A contract:
  (a) default --limit 0 exports all filtered pages,
  (b) --limit N truncates to the first N,
  (c) an unsatisfiable --query / --tag yields "No pages to export." (guard path),
  (d) --format html emits a DOCTYPE + <table>.
"""

from __future__ import annotations

import os

from click.testing import CliRunner

from personal_index.cli import main


def _seed_pages(dd: str, n: int = 3) -> None:
    """Seed n distinct pages into the scratch data dir."""
    for i in range(n):
        path = os.path.join(dd, f"page{i}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"distinct content alpha{i} beta gamma")
        res = CliRunner().invoke(main, ["import", path, "--data-dir", dd])
        assert res.exit_code == 0, res.output


class TestReachableExportCommand:
    """End-to-end pins for the reachable `personal-index export` (Option A)."""

    def test_default_limit_zero_exports_all(self, tmp_path):
        """(a) default --limit 0 exports every page (no truncation)."""
        dd = str(tmp_path)
        runner = CliRunner()
        assert runner.invoke(main, ["init", "--data-dir", dd]).exit_code == 0
        _seed_pages(dd, 3)

        res = runner.invoke(main, ["export", "--format", "markdown", "--data-dir", dd])
        assert res.exit_code == 0, res.output
        assert "Total pages: 3" in res.output
        for i in range(3):
            assert f"page{i}.txt" in res.output

    def test_limit_n_truncates(self, tmp_path):
        """(b) --limit N truncates to the first N of the filtered set."""
        dd = str(tmp_path)
        runner = CliRunner()
        assert runner.invoke(main, ["init", "--data-dir", dd]).exit_code == 0
        _seed_pages(dd, 3)

        res = runner.invoke(main, ["export", "--format", "markdown",
                                   "--limit", "2", "--data-dir", dd])
        assert res.exit_code == 0, res.output
        assert "Total pages: 2" in res.output

    def test_unsatisfiable_query_guard(self, tmp_path):
        """(c) unsatisfiable --query -> empty result -> 'No pages to export.'"""
        dd = str(tmp_path)
        runner = CliRunner()
        assert runner.invoke(main, ["init", "--data-dir", dd]).exit_code == 0
        _seed_pages(dd, 3)

        res = runner.invoke(main, ["export", "--query", "zzzznomatch",
                                   "--data-dir", dd])
        assert res.exit_code == 0, res.output
        assert "No pages to export." in res.output

    def test_unsatisfiable_tag_guard(self, tmp_path):
        """(c) unsatisfiable --tag -> empty result -> 'No pages to export.'"""
        dd = str(tmp_path)
        runner = CliRunner()
        assert runner.invoke(main, ["init", "--data-dir", dd]).exit_code == 0
        _seed_pages(dd, 3)

        res = runner.invoke(main, ["export", "--tag", "no-such-tag",
                                   "--data-dir", dd])
        assert res.exit_code == 0, res.output
        assert "No pages to export." in res.output

    def test_html_format_emits_doctype_and_table(self, tmp_path):
        """(d) --format html emits a DOCTYPE + <table>."""
        dd = str(tmp_path)
        runner = CliRunner()
        assert runner.invoke(main, ["init", "--data-dir", dd]).exit_code == 0
        _seed_pages(dd, 3)

        res = runner.invoke(main, ["export", "--format", "html", "--data-dir", dd])
        assert res.exit_code == 0, res.output
        assert "<!DOCTYPE html>" in res.output
        assert "<table>" in res.output

    def test_reachable_option_set(self, tmp_path):
        """The reachable export advertises the full Option A option set."""
        res = CliRunner().invoke(main, ["export", "--help"])
        assert res.exit_code == 0, res.output
        for opt in ("--format", "--tag", "--query", "--limit", "--output"):
            assert opt in res.output
        # html is a reachable format choice
        assert "html" in res.output
