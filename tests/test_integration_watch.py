"""Integration tests for the watch command."""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import pytest
from click.testing import CliRunner

from personal_index.cli import main


class TestWatchCommand:
    """Test the watch command."""

    def test_watch_nonexistent_path(self, tmp_path, monkeypatch):
        """Test watching a non-existent path."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(main, ["watch", "/nonexistent/path"])
        assert result.exit_code != 0

    def test_watch_single_file(self, tmp_path, monkeypatch):
        """Test watching a single file (quick exit)."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        # Create initial file
        article = tmp_path / "article.txt"
        article.write_text("Initial content about Python.")

        # Run watch once to verify it works
        result = runner.invoke(main, ["watch", str(article), "--interval", "1", "--once"])
        assert result.exit_code == 0
        assert "Watching" in result.output

    def test_watch_directory(self, tmp_path, monkeypatch):
        """Test watching a directory."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        docs = tmp_path / "docs"
        docs.mkdir()

        result = runner.invoke(main, ["watch", str(docs), "--interval", "1", "--once"])
        assert result.exit_code == 0
