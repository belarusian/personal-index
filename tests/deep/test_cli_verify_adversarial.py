"""Adversarial deep tests for the `verify` CLI command (personal_index/cli.py).

The live `verify` command is registered via @main.command() in cli.py and
checks three data stores (search index, tag store, interest store) plus
optional subdirectory existence. It must degrade gracefully on corrupted
or missing data files, handle unicode paths, and be idempotent.
"""

import json

from click.testing import CliRunner

from personal_index.cli import main


def _write_json(path: str, data) -> None:
    with open(path, "w") as f:
        json.dump(data, f)


def _write_text(path: str, content: str) -> None:
    with open(path, "w") as f:
        f.write(content)


class TestVerifyEmptyDataDir:
    """Fresh (empty) data directory: all stores should report zero counts."""

    def test_fresh_dir_all_checks_pass(self, tmp_path):
        runner = CliRunner()
        r = runner.invoke(main, ["verify", "--data-dir", str(tmp_path)])
        assert r.exit_code == 0
        assert "All checks passed" in r.output

    def test_fresh_dir_reports_zero_pages(self, tmp_path):
        runner = CliRunner()
        r = runner.invoke(main, ["verify", "--data-dir", str(tmp_path)])
        assert r.exit_code == 0
        # Search index should report 0 pages
        assert "0" in r.output

    def test_fresh_dir_creates_directory(self, tmp_path):
        target = tmp_path / "new_subdir"
        runner = CliRunner()
        r = runner.invoke(main, ["verify", "--data-dir", str(target)])
        assert r.exit_code == 0
        assert target.is_dir()


class TestVerifyCorruptedFiles:
    """Corrupted JSON files must not crash verify; stores degrade to empty."""

    def test_corrupted_search_index(self, tmp_path):
        _write_text(str(tmp_path / "search_index.json"), "{invalid json!!")
        runner = CliRunner()
        r = runner.invoke(main, ["verify", "--data-dir", str(tmp_path)])
        assert r.exit_code == 0
        assert "All checks passed" in r.output

    def test_corrupted_tags_json(self, tmp_path):
        _write_text(str(tmp_path / "tags.json"), "not json at all")
        runner = CliRunner()
        r = runner.invoke(main, ["verify", "--data-dir", str(tmp_path)])
        assert r.exit_code == 0
        assert "All checks passed" in r.output

    def test_corrupted_interests_json(self, tmp_path):
        _write_text(str(tmp_path / "interests.json"), "[1, 2, 3]")
        runner = CliRunner()
        r = runner.invoke(main, ["verify", "--data-dir", str(tmp_path)])
        assert r.exit_code == 0
        assert "All checks passed" in r.output

    def test_all_three_corrupted(self, tmp_path):
        _write_text(str(tmp_path / "search_index.json"), "garbage")
        _write_text(str(tmp_path / "tags.json"), "garbage")
        _write_text(str(tmp_path / "interests.json"), "garbage")
        runner = CliRunner()
        r = runner.invoke(main, ["verify", "--data-dir", str(tmp_path)])
        assert r.exit_code == 0
        assert "All checks passed" in r.output

    def test_empty_file_search_index(self, tmp_path):
        _write_text(str(tmp_path / "search_index.json"), "")
        runner = CliRunner()
        r = runner.invoke(main, ["verify", "--data-dir", str(tmp_path)])
        assert r.exit_code == 0

    def test_empty_file_tags(self, tmp_path):
        _write_text(str(tmp_path / "tags.json"), "")
        runner = CliRunner()
        r = runner.invoke(main, ["verify", "--data-dir", str(tmp_path)])
        assert r.exit_code == 0

    def test_empty_file_interests(self, tmp_path):
        _write_text(str(tmp_path / "interests.json"), "")
        runner = CliRunner()
        r = runner.invoke(main, ["verify", "--data-dir", str(tmp_path)])
        assert r.exit_code == 0


class TestVerifyUnicodeAndEdgePaths:
    """Unicode and unusual data directory paths."""

    def test_unicode_data_dir(self, tmp_path):
        target = tmp_path / "данные_测试_📁"
        runner = CliRunner()
        r = runner.invoke(main, ["verify", "--data-dir", str(target)])
        assert r.exit_code == 0
        assert "All checks passed" in r.output

    def test_whitespace_data_dir(self, tmp_path):
        target = tmp_path / "  spaced dir  "
        runner = CliRunner()
        r = runner.invoke(main, ["verify", "--data-dir", str(target)])
        assert r.exit_code == 0

    def test_nested_data_dir(self, tmp_path):
        target = tmp_path / "a" / "b" / "c" / "deep"
        runner = CliRunner()
        r = runner.invoke(main, ["verify", "--data-dir", str(target)])
        assert r.exit_code == 0
        assert target.is_dir()


class TestVerifyQuickFlag:
    """--quick skips subdirectory checks."""

    def test_quick_skips_subdir_checks(self, tmp_path):
        runner = CliRunner()
        r = runner.invoke(main, ["verify", "--quick", "--data-dir", str(tmp_path)])
        assert r.exit_code == 0
        # Subdir checks (cache, archive, backups) should NOT appear
        assert "Directory: cache" not in r.output
        assert "Directory: archive" not in r.output
        assert "Directory: backups" not in r.output

    def test_full_includes_subdir_checks(self, tmp_path):
        runner = CliRunner()
        r = runner.invoke(main, ["verify", "--data-dir", str(tmp_path)])
        assert r.exit_code == 0
        # Subdir checks should appear (they'll fail since dirs don't exist)
        assert "Directory: cache" in r.output
        assert "Directory: archive" in r.output
        assert "Directory: backups" in r.output


class TestVerifyIdempotence:
    """Running verify twice on the same data dir should give the same result."""

    def test_idempotent_fresh(self, tmp_path):
        runner = CliRunner()
        r1 = runner.invoke(main, ["verify", "--data-dir", str(tmp_path)])
        r2 = runner.invoke(main, ["verify", "--data-dir", str(tmp_path)])
        assert r1.exit_code == 0
        assert r2.exit_code == 0
        assert r1.output == r2.output

    def test_idempotent_with_data(self, tmp_path):
        # Seed some data
        from personal_index.index import SearchIndex
        from personal_index.models import CrawledPage

        idx = SearchIndex(db_path=str(tmp_path / "search_index.json"))
        idx.add_page(CrawledPage(url="http://test.com", title="Test", content="Hello world content"))
        idx._save()

        runner = CliRunner()
        r1 = runner.invoke(main, ["verify", "--data-dir", str(tmp_path)])
        r2 = runner.invoke(main, ["verify", "--data-dir", str(tmp_path)])
        assert r1.exit_code == 0
        assert r2.exit_code == 0
        assert r1.output == r2.output


class TestVerifyWithData:
    """Verify with pre-existing data reports correct counts."""

    def test_reports_page_count(self, tmp_path):
        from personal_index.index import SearchIndex
        from personal_index.models import CrawledPage

        idx = SearchIndex(db_path=str(tmp_path / "search_index.json"))
        idx.add_page(CrawledPage(url="http://a.com", title="A", content="Content A here"))
        idx.add_page(CrawledPage(url="http://b.com", title="B", content="Content B here"))
        idx._save()

        runner = CliRunner()
        r = runner.invoke(main, ["verify", "--data-dir", str(tmp_path)])
        assert r.exit_code == 0
        assert "2" in r.output

    def test_reports_tag_count(self, tmp_path):
        from personal_index.tags import TagStore

        ts = TagStore(store_path=str(tmp_path / "tags.json"))
        ts.add_tag_to_page("http://test.com", "python")
        ts.add_tag_to_page("http://test.com", "web")
        ts._save()

        runner = CliRunner()
        r = runner.invoke(main, ["verify", "--data-dir", str(tmp_path)])
        assert r.exit_code == 0
        assert "2" in r.output

    def test_reports_interest_count(self, tmp_path):
        from personal_index.interests import InterestStore
        from personal_index.models import Interest

        ist = InterestStore(store_path=str(tmp_path / "interests.json"))
        ist.add(Interest(name="python", keywords=["python"]))
        ist.add(Interest(name="web", keywords=["web"]))
        ist._save()

        runner = CliRunner()
        r = runner.invoke(main, ["verify", "--data-dir", str(tmp_path)])
        assert r.exit_code == 0
        assert "2" in r.output


class TestVerifySubdirs:
    """Subdirectory checks (cache, archive, backups)."""

    def test_all_subdirs_present(self, tmp_path):
        for d in ["cache", "archive", "backups"]:
            (tmp_path / d).mkdir()
        runner = CliRunner()
        r = runner.invoke(main, ["verify", "--data-dir", str(tmp_path)])
        assert r.exit_code == 0
        assert "missing" not in r.output

    def test_no_subdirs_present(self, tmp_path):
        runner = CliRunner()
        r = runner.invoke(main, ["verify", "--data-dir", str(tmp_path)])
        assert r.exit_code == 0
        assert "missing" in r.output

    def test_partial_subdirs(self, tmp_path):
        (tmp_path / "cache").mkdir()
        runner = CliRunner()
        r = runner.invoke(main, ["verify", "--data-dir", str(tmp_path)])
        assert r.exit_code == 0
        # cache present, archive and backups missing
        assert "Directory: cache/" in r.output
        assert "missing" in r.output


class TestVerifyNonDictJson:
    """JSON files that parse but are not dicts (lists, strings, numbers)."""

    def test_search_index_is_list(self, tmp_path):
        _write_json(str(tmp_path / "search_index.json"), [1, 2, 3])
        runner = CliRunner()
        r = runner.invoke(main, ["verify", "--data-dir", str(tmp_path)])
        assert r.exit_code == 0

    def test_tags_is_string(self, tmp_path):
        _write_json(str(tmp_path / "tags.json"), "just a string")
        runner = CliRunner()
        r = runner.invoke(main, ["verify", "--data-dir", str(tmp_path)])
        assert r.exit_code == 0

    def test_interests_is_number(self, tmp_path):
        _write_json(str(tmp_path / "interests.json"), 42)
        runner = CliRunner()
        r = runner.invoke(main, ["verify", "--data-dir", str(tmp_path)])
        assert r.exit_code == 0


class TestVerifyEndToEnd:
    """End-to-end CLI run through the installed entry point."""

    def test_e2e_fresh_to_verify(self, tmp_path):
        """Full lifecycle: create dir, verify, add data, verify again."""
        runner = CliRunner()

        # First verify on empty dir
        r1 = runner.invoke(main, ["verify", "--data-dir", str(tmp_path)])
        assert r1.exit_code == 0

        # Add a page
        from personal_index.index import SearchIndex
        from personal_index.models import CrawledPage

        idx = SearchIndex(db_path=str(tmp_path / "search_index.json"))
        idx.add_page(CrawledPage(url="http://e2e.com", title="E2E", content="End to end test content"))
        idx._save()

        # Second verify should see the page
        r2 = runner.invoke(main, ["verify", "--data-dir", str(tmp_path)])
        assert r2.exit_code == 0
        assert "1" in r2.output
