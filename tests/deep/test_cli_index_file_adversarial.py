"""Adversarial deep tests for the single file-indexing helper in personal_index.cli.

Cycle 151 - VALIDATOR VERIFY of ARCH-11 (tickets/ARCH-11.md, #1016).

ARCH-11 contract (the code is the truth):
  - The dead ``_index_file`` helper was removed. The ONLY file-indexing helper
    is ``_index_file_once(fp, data_dir) -> None``: it reads the file
    (``errors="replace"``), returns WITHOUT indexing when
    ``len(content.strip()) < 10`` (guard path), else builds a ``CrawledPage``
    and calls ``idx.add_page(page)`` (main path).
  - ``_watch_once`` indexes every collected file via ``_index_file_once`` and
    there is EXACTLY ONE file-indexing helper used by it.

Tests:
  - watch --once (click CliRunner) indexes a valid file (>= 10 chars) and
    skips a short file (< 10 chars) in one run.
  - empty and whitespace-only files are NOT indexed (guard path).
  - the module exposes exactly one file-indexing helper: ``_index_file_once``
    present, dead ``_index_file`` absent, and ``_watch_once`` references the
    live helper (pins "exactly one").
  - one end-to-end run through the installed CLI entry point.
"""

from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

import pytest

from click.testing import CliRunner

from personal_index.cli import get_search_index, main


VALID_CONTENT = "This is a valid article with enough content to be indexed."


def _run_watch_once(paths: list[str], dd: str) -> "CliRunner":
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["watch", *paths, "--once", "--data-dir", dd],
    )
    assert result.exit_code == 0, result.output
    return result


class TestWatchOnceUsesIndexFileOnce:
    """Pin that watch --once indexes via the live _index_file_once helper."""

    def test_valid_indexed_short_skipped(self, tmp_path):
        """Main path (valid file indexed) + guard path (short file skipped)."""
        dd = str(tmp_path / "data")
        valid = tmp_path / "valid.txt"
        valid.write_text(VALID_CONTENT)
        short = tmp_path / "short.txt"
        short.write_text("short")  # 5 chars < 10

        _run_watch_once([str(valid), str(short)], dd)

        idx = get_search_index(dd)
        assert idx.get_page(f"file://{valid}") is not None
        assert idx.get_page(f"file://{short}") is None
        assert idx.get_page_count() == 1

    def test_empty_file_not_indexed(self, tmp_path):
        """Guard path: a zero-byte file is not indexed."""
        dd = str(tmp_path / "data")
        empty = tmp_path / "empty.txt"
        empty.write_text("")

        _run_watch_once([str(empty)], dd)

        idx = get_search_index(dd)
        assert idx.get_page(f"file://{empty}") is None
        assert idx.get_page_count() == 0

    def test_whitespace_only_file_not_indexed(self, tmp_path):
        """Guard path: whitespace-only content strips to < 10 chars -> skipped."""
        dd = str(tmp_path / "data")
        ws = tmp_path / "ws.txt"
        ws.write_text("   \n\t\n   ")  # strips to "" -> len 0 < 10

        _run_watch_once([str(ws)], dd)

        idx = get_search_index(dd)
        assert idx.get_page(f"file://{ws}") is None
        assert idx.get_page_count() == 0

    def test_directory_recursion_indexes_valid_skips_short(self, tmp_path):
        """A directory path is collected recursively; guard still applies."""
        dd = str(tmp_path / "data")
        d = tmp_path / "docs"
        d.mkdir()
        (d / "good.txt").write_text(VALID_CONTENT)
        (d / "tiny.txt").write_text("nope")

        _run_watch_once([str(d)], dd)

        idx = get_search_index(dd)
        assert idx.get_page(f"file://{d / 'good.txt'}") is not None
        assert idx.get_page(f"file://{d / 'tiny.txt'}") is None
        assert idx.get_page_count() == 1


class TestExactlyOneFileIndexingHelper:
    """Pin 'exactly one file-indexing helper' (ARCH-11 acceptance criterion)."""

    def test_dead_index_file_removed(self):
        """The dead _index_file helper must be gone from the module."""
        import personal_index.cli as cli

        assert not hasattr(cli, "_index_file"), (
            "dead _index_file helper still present; ARCH-11 requires it removed "
            "or wired into a live path"
        )

    def test_live_helper_present(self):
        """The live _index_file_once helper must exist."""
        import personal_index.cli as cli

        assert hasattr(cli, "_index_file_once")
        assert callable(cli._index_file_once)

    def test_watch_once_references_live_helper(self):
        """_watch_once must call the live helper (single live path)."""
        import personal_index.cli as cli

        src = inspect.getsource(cli._watch_once)
        assert "_index_file_once" in src
        # the dead helper must not be referenced by the live path
        assert "_index_file(" not in src.replace("_index_file_once(", "")


class TestEndToEndCLI:
    """One end-to-end run through the installed CLI entry point."""

    def test_watch_once_via_entry_point(self, tmp_path):
        """Run the installed `personal-index` CLI watch --once end to end."""
        dd = str(tmp_path / "data")
        valid = tmp_path / "valid.txt"
        valid.write_text(VALID_CONTENT)

        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "personal_index.cli",
                "watch",
                str(valid),
                "--once",
                "--data-dir",
                dd,
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr

        idx = get_search_index(dd)
        assert idx.get_page(f"file://{valid}") is not None
        assert idx.get_page_count() == 1
