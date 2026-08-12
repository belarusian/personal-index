"""End-to-end CLI tests for tags management."""

from __future__ import annotations

import os

from click.testing import CliRunner

from personal_index.cli import main
from personal_index.tags import TagStore


class TestCLITagsE2E:
    """Test tags CLI commands end-to-end."""

    def test_tags_add_list(self, tmp_path, monkeypatch):
        """Test adding and listing tags."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(main, [
            "tags", "add", "important", "https://example.com/page1",
        ])
        assert result.exit_code == 0

        result = runner.invoke(main, ["tags", "list"])
        assert result.exit_code == 0
        assert "important" in result.output.lower()

    def test_tags_add_multiple_pages(self, tmp_path, monkeypatch):
        """Test adding tag to multiple pages."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, [
            "tags", "add", "tutorial",
            "https://example.com/page1",
            "https://example.com/page2",
        ])
        assert runner.invoke(main, ["tags", "list"]).exit_code == 0

    def test_tags_remove(self, tmp_path, monkeypatch):
        """Test removing a tag."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, [
            "tags", "add", "temp", "https://example.com/page1",
        ])
        result = runner.invoke(main, ["tags", "remove", "temp", "https://example.com/page1"])
        assert result.exit_code == 0

    def test_tags_persistence(self, tmp_path, monkeypatch):
        """Test tags persist to disk."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, [
            "tags", "add", "test", "https://example.com/page1",
        ])

        store = TagStore(
            store_path=os.path.join(".personal_index", "tags.json")
        )
        assert store.get_tag_count() > 0
