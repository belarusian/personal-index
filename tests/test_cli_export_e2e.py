"""End-to-end CLI tests for export command."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock

from click.testing import CliRunner

from personal_index.cli import main


class TestCLIExportE2E:
    """Test export CLI commands end-to-end."""

    def test_export_markdown(self, tmp_path, monkeypatch):
        """Test exporting index as markdown."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Create and index a file
        test_file = tmp_path / "article.txt"
        test_file.write_text("# Test\n\nTest content for export.")

        runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--min-content-length", "10",
        ])

        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0

    def test_export_json(self, tmp_path, monkeypatch):
        """Test exporting index as JSON."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("# Test\n\nTest content for export.")

        runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--min-content-length", "10",
        ])

        result = runner.invoke(main, ["export", "--format", "json"])
        assert result.exit_code == 0

    def test_export_csv(self, tmp_path, monkeypatch):
        """Test exporting index as CSV."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("# Test\n\nTest content for export.")

        runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--min-content-length", "10",
        ])

        result = runner.invoke(main, ["export", "--format", "csv"])
        assert result.exit_code == 0

    def test_export_empty_index(self, tmp_path, monkeypatch):
        """Test exporting an empty index."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0

    def test_load_pages_returns_all_when_no_filters(self, tmp_path, monkeypatch):
        """Test _load_pages returns all pages when no filters applied."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("# Test\n\nTest content for export.")

        runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--min-content-length", "10",
        ])

        from personal_index.cli_export import _load_pages
        from personal_index.index import SearchIndex
        from personal_index.tags import TagStore

        index = SearchIndex(db_path=os.path.join(".personal_index", "search_index.json"))
        tag_store = TagStore(store_path=os.path.join(".personal_index", "tags.json"))

        pages = _load_pages(index, tag_store, query=None, tag=(), limit=0)
        assert len(pages) >= 1

    def test_load_pages_filters_by_query(self, tmp_path, monkeypatch):
        """Test _load_pages filters pages by search query."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("# Python Tutorial\n\nLearn Python programming.")

        runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--min-content-length", "10",
        ])

        from personal_index.cli_export import _load_pages
        from personal_index.index import SearchIndex
        from personal_index.tags import TagStore

        index = SearchIndex(db_path=os.path.join(".personal_index", "search_index.json"))
        tag_store = TagStore(store_path=os.path.join(".personal_index", "tags.json"))

        # Without query filter, should get pages
        pages_all = _load_pages(index, tag_store, query=None, tag=(), limit=0)
        assert len(pages_all) >= 1

        # With query filter, should get matching pages (subset of all)
        pages_filtered = _load_pages(index, tag_store, query="python", tag=(), limit=0)
        assert len(pages_filtered) <= len(pages_all)

    def test_load_pages_applies_limit(self, tmp_path, monkeypatch):
        """Test _load_pages respects the limit parameter."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        for i in range(5):
            test_file = tmp_path / f"article_{i}.txt"
            test_file.write_text(f"# Article {i}\n\nContent for article {i}.")
            runner.invoke(main, [
                "pipeline", "--import-file", str(test_file),
                "--min-content-length", "10",
            ])

        from personal_index.cli_export import _load_pages
        from personal_index.index import SearchIndex
        from personal_index.tags import TagStore

        index = SearchIndex(db_path=os.path.join(".personal_index", "search_index.json"))
        tag_store = TagStore(store_path=os.path.join(".personal_index", "tags.json"))

        pages = _load_pages(index, tag_store, query=None, tag=(), limit=2)
        assert len(pages) == 2

    def test_load_pages_with_mock_tag_filter(self):
        """Test _load_pages tag filtering with mocked dependencies."""
        from personal_index.cli_export import _load_pages

        # Mock index returning pages
        mock_index = MagicMock()
        mock_page1 = MagicMock(url="http://example.com/1", title="Page 1")
        mock_page2 = MagicMock(url="http://example.com/2", title="Page 2")
        mock_index.list_pages.return_value = [mock_page1, mock_page2]

        # Mock tag store
        mock_tag_store = MagicMock()
        mock_tag_store.get_tags_for_page.side_effect = lambda url: {
            "http://example.com/1": ["tag-a"],
            "http://example.com/2": ["tag-b"],
        }.get(url, [])

        pages = _load_pages(mock_index, mock_tag_store, query=None, tag=("tag-a",), limit=0)
        assert len(pages) == 1
        assert pages[0].url == "http://example.com/1"

    def test_dispatch_format_markdown(self, tmp_path, monkeypatch):
        """Test _dispatch_format returns markdown output."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("# Test\n\nTest content.")

        runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--min-content-length", "10",
        ])

        from personal_index.cli_export import _dispatch_format
        from personal_index.index import SearchIndex
        from personal_index.tags import TagStore

        index = SearchIndex(db_path=os.path.join(".personal_index", "search_index.json"))
        tag_store = TagStore(store_path=os.path.join(".personal_index", "tags.json"))
        pages = index.list_pages()

        output = _dispatch_format("markdown", pages, tag_store)
        assert "# Personal Index Export" in output

    def test_dispatch_format_json(self, tmp_path, monkeypatch):
        """Test _dispatch_format returns JSON output."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("# Test\n\nTest content.")

        runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--min-content-length", "10",
        ])

        from personal_index.cli_export import _dispatch_format
        from personal_index.index import SearchIndex
        from personal_index.tags import TagStore

        index = SearchIndex(db_path=os.path.join(".personal_index", "search_index.json"))
        tag_store = TagStore(store_path=os.path.join(".personal_index", "tags.json"))
        pages = index.list_pages()

        output = _dispatch_format("json", pages, tag_store)
        parsed = json.loads(output)
        assert isinstance(parsed, list)

    def test_dispatch_format_csv(self, tmp_path, monkeypatch):
        """Test _dispatch_format returns CSV output."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("# Test\n\nTest content.")

        runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--min-content-length", "10",
        ])

        from personal_index.cli_export import _dispatch_format
        from personal_index.index import SearchIndex
        from personal_index.tags import TagStore

        index = SearchIndex(db_path=os.path.join(".personal_index", "search_index.json"))
        tag_store = TagStore(store_path=os.path.join(".personal_index", "tags.json"))
        pages = index.list_pages()

        output = _dispatch_format("csv", pages, tag_store)
        assert "url,title,score,tags,content_length" in output

    def test_dispatch_format_html(self, tmp_path, monkeypatch):
        """Test _dispatch_format returns HTML output."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("# Test\n\nTest content.")

        runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--min-content-length", "10",
        ])

        from personal_index.cli_export import _dispatch_format
        from personal_index.index import SearchIndex
        from personal_index.tags import TagStore

        index = SearchIndex(db_path=os.path.join(".personal_index", "search_index.json"))
        tag_store = TagStore(store_path=os.path.join(".personal_index", "tags.json"))
        pages = index.list_pages()

        output = _dispatch_format("html", pages, tag_store)
        assert "<!DOCTYPE html>" in output
        assert "<table>" in output
