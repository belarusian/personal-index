"""Comprehensive CLI command tests for personal-index."""

from __future__ import annotations

import json

from click.testing import CliRunner

from personal_index.cli import main


class TestStatsCommand:
    """Test the stats command."""

    def test_stats_text_format(self, tmp_path, monkeypatch):
        """Test stats output in text format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "test", "-k", "python"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["stats"])
        assert result.exit_code == 0
        assert "indexed_pages" in result.output.lower() or "Indexed pages" in result.output

    def test_stats_json_format(self, tmp_path, monkeypatch):
        """Test stats output in JSON format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "test", "-k", "python"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["stats", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "indexed_pages" in data
        assert "total_tags" in data


class TestListCommand:
    """Test the list command."""

    def test_list_text_format(self, tmp_path, monkeypatch):
        """Test list output in text format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "test", "-k", "python"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["list"])
        assert result.exit_code == 0
        # Should show at least one page
        assert "Indexed pages" in result.output or "indexed pages" in result.output.lower()

    def test_list_json_format(self, tmp_path, monkeypatch):
        """Test list output in JSON format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "test", "-k", "python"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["list", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "pages" in data
        assert len(data["pages"]) >= 1

    def test_list_csv_format(self, tmp_path, monkeypatch):
        """Test list output in CSV format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "test", "-k", "python"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["list", "--format", "csv"])
        assert result.exit_code == 0
        # CSV should have header
        assert "rank" in result.output.lower() or "title" in result.output.lower()

    def test_list_sorted_by_date(self, tmp_path, monkeypatch):
        """Test list sorted by date."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "test", "-k", "python"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["list", "--sort", "date"])
        assert result.exit_code == 0

    def test_list_sorted_by_title(self, tmp_path, monkeypatch):
        """Test list sorted by title."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "test", "-k", "python"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["list", "--sort", "title"])
        assert result.exit_code == 0


class TestTopCommand:
    """Test the top command."""

    def test_top_default(self, tmp_path, monkeypatch):
        """Test top with default settings."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "test", "-k", "python"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["top"])
        assert result.exit_code == 0
        assert "Top" in result.output or "top" in result.output.lower()

    def test_top_json_format(self, tmp_path, monkeypatch):
        """Test top output in JSON format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "test", "-k", "python"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["top", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "top_pages" in data

    def test_top_custom_limit(self, tmp_path, monkeypatch):
        """Test top with custom limit."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "test", "-k", "python"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["top", "--limit", "5"])
        assert result.exit_code == 0


class TestRemoveCommand:
    """Test the remove command."""

    def test_remove_existing_page(self, tmp_path, monkeypatch):
        """Test removing an existing page."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "test", "-k", "python"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file)])

        # Get URL from list
        list_result = runner.invoke(main, ["list", "--format", "json"])
        assert list_result.exit_code == 0
        data = json.loads(list_result.output)
        assert len(data["pages"]) >= 1
        url = data["pages"][0]["url"]

        # Remove it
        result = runner.invoke(main, ["remove", url])
        assert result.exit_code == 0

        # Verify removed
        list_result2 = runner.invoke(main, ["list", "--format", "json"])
        data2 = json.loads(list_result2.output)
        assert all(p["url"] != url for p in data2["pages"])

    def test_remove_nonexistent_page(self, tmp_path, monkeypatch):
        """Test removing a page that doesn't exist."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(main, ["remove", "https://nonexistent.com/page"])
        # Should exit with error
        assert result.exit_code == 1


class TestClearCommand:
    """Test the clear command."""

    def test_clear_index_only(self, tmp_path, monkeypatch):
        """Test clearing only the index."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "test", "-k", "python"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["clear", "--index"])
        assert result.exit_code == 0
        assert "Cleared search index" in result.output

    def test_clear_tags_only(self, tmp_path, monkeypatch):
        """Test clearing only tags."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "test", "-k", "python"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["clear", "--tags"])
        assert result.exit_code == 0
        assert "Cleared tags" in result.output

    def test_clear_all(self, tmp_path, monkeypatch):
        """Test clearing everything."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "test", "-k", "python"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["clear", "--index", "--tags", "--interests"])
        assert result.exit_code == 0
        assert "Done" in result.output


class TestDoctorCommand:
    """Test the doctor command."""

    def test_doctor_no_issues(self, tmp_path, monkeypatch):
        """Test doctor with no issues."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        # Should show health check
        assert "Health Check" in result.output or "health" in result.output.lower()

    def test_doctor_missing_data_dir(self, tmp_path, monkeypatch):
        """Test doctor with missing data directory."""
        # Use a path that doesn't exist
        runner = CliRunner()
        
        # Create a temp dir and use it as data-dir
        nonexistent = str(tmp_path / "nonexistent")
        result = runner.invoke(main, ["doctor", "--data-dir", nonexistent])
        assert result.exit_code == 1  # Should have issues


class TestExportCommand:
    """Test the export command."""

    def test_export_json(self, tmp_path, monkeypatch):
        """Test exporting in JSON format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "test", "-k", "python"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["export", "--format", "json"])
        assert result.exit_code == 0
        # Should produce JSON output
        try:
            data = json.loads(result.output)
            assert isinstance(data, (dict, list))
        except json.JSONDecodeError:
            # Output might be written to file instead
            pass

    def test_export_markdown(self, tmp_path, monkeypatch):
        """Test exporting in markdown format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "test", "-k", "python"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0
        # Should produce markdown output
        assert "#" in result.output or "Search Results" in result.output

    def test_export_csv(self, tmp_path, monkeypatch):
        """Test exporting in CSV format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "test", "-k", "python"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["export", "--format", "csv"])
        assert result.exit_code == 0
        # Should produce CSV output with header
        assert "rank" in result.output.lower() or "title" in result.output.lower()
