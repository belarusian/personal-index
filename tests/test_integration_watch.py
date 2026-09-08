"""Integration tests for the watch command."""

from __future__ import annotations

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


class TestWatchOnceBehavior:
    """Pin the exact contract of _watch_once (TICKET-515)."""

    def test_file_dir_and_skip_and_error(self, tmp_path, monkeypatch):
        """File + dir are indexed, non-existent path skipped, per-file error caught."""
        from personal_index.cli import _watch_once, get_search_index

        dd = str(tmp_path / "data")
        # a regular file with enough content to be indexed
        f = tmp_path / "article.txt"
        f.write_text("Initial content about Python.")
        # a directory containing one indexable file
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "note.md").write_text("A note about testing things.")
        # a non-existent path -> guard/skip branch
        missing = tmp_path / "does-not-exist"

        _watch_once((str(f), str(docs), str(missing)), dd)

        idx = get_search_index(dd)
        # file + dir-file indexed; the missing path contributed nothing
        assert idx.get_page_count() == 2
        assert idx.get_page(f"file://{f}") is not None
        assert idx.get_page(f"file://{docs / 'note.md'}") is not None

    def test_per_file_error_caught_and_loop_continues(self, tmp_path, monkeypatch):
        """A per-file exception is caught+echoed and the loop continues."""
        from personal_index import cli
        from personal_index.cli import _watch_once, get_search_index

        dd = str(tmp_path / "data")
        f1 = tmp_path / "a.txt"
        f1.write_text("First file content here.")
        f2 = tmp_path / "b.txt"
        f2.write_text("Second file content here.")

        real = cli._index_file_once
        def flaky(fp, data_dir):
            if fp.endswith("a.txt"):
                raise RuntimeError("boom")
            real(fp, data_dir)
        monkeypatch.setattr(cli, "_index_file_once", flaky)

        _watch_once((str(f1), str(f2)), dd)

        idx = get_search_index(dd)
        # a.txt raised and was skipped; b.txt still indexed (loop continued)
        assert idx.get_page_count() == 1
        assert idx.get_page(f"file://{f2}") is not None


class TestWatchOnceUsesIndexFileOnce:
    """Pin that watch --once indexes via the live _index_file_once helper (ARCH-11).

    The dead _index_file helper was removed; the only file-indexing helper is
    _index_file_once, whose guard path skips files shorter than 10 chars. This
    test pins both the main path (valid file indexed) and the guard path (short
    file skipped) in one test, so a regression that re-introduces a dead or
    alternate indexing helper is caught.
    """

    def test_watch_once_uses_index_file_once(self, tmp_path):
        """watch --once indexes the valid file and skips the short file."""
        from click.testing import CliRunner

        from personal_index.cli import get_search_index, main

        dd = str(tmp_path / "data")
        valid = tmp_path / "valid.txt"
        valid.write_text("This is a valid article with enough content.")
        short = tmp_path / "short.txt"
        short.write_text("short")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["watch", str(valid), str(short), "--once", "--data-dir", dd],
        )
        assert result.exit_code == 0

        idx = get_search_index(dd)
        # main path: the valid file (>= 10 chars) is indexed
        assert idx.get_page(f"file://{valid}") is not None
        # guard path: the short file (< 10 chars) is NOT indexed
        assert idx.get_page(f"file://{short}") is None
        assert idx.get_page_count() == 1
