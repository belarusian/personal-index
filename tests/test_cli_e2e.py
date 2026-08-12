"""CLI end-to-end integration tests.

Tests the actual CLI commands work correctly with real file I/O.
"""

from __future__ import annotations

import json
import os

from personal_index.cli import main


class TestCLIInit:
    """Test the 'init' command."""

    def test_init_creates_data_dir(self, tmp_path, monkeypatch):
        """init should create the data directory structure."""
        monkeypatch.chdir(tmp_path)
        main(['init'], standalone_mode=False)
        assert os.path.isdir(str(tmp_path / ".personal_index"))
        assert os.path.isdir(str(tmp_path / ".personal_index" / "cache"))
        assert os.path.isdir(str(tmp_path / ".personal_index" / "archive"))
        assert os.path.isdir(str(tmp_path / ".personal_index" / "backups"))

    def test_init_creates_config(self, tmp_path, monkeypatch):
        """init should create a default config.yaml."""
        monkeypatch.chdir(tmp_path)
        main(['init'], standalone_mode=False)
        assert os.path.isfile(str(tmp_path / "config.yaml"))
        with open(tmp_path / "config.yaml") as f:
            import yaml
            config = yaml.safe_load(f)
        assert "crawler" in config
        assert "filter" in config

    def test_init_idempotent(self, tmp_path, monkeypatch):
        """Running init twice should not error."""
        monkeypatch.chdir(tmp_path)
        main(['init'], standalone_mode=False)
        main(['init'], standalone_mode=False)  # Should not raise


class TestCLIInterests:
    """Test the 'interests' command group."""

    def _setup(self, tmp_path, monkeypatch):
        """Set up a fresh project."""
        monkeypatch.chdir(tmp_path)
        main(['init'], standalone_mode=False)

    def test_interests_add(self, tmp_path, monkeypatch):
        """Should add an interest."""
        self._setup(tmp_path, monkeypatch)
        main(['interests', 'add', '--name', 'python', '-k', 'python', '-k', 'programming'],
             standalone_mode=False)
        # Verify it was saved
        with open(tmp_path / ".personal_index" / "interests.json") as f:
            data = json.load(f)
        assert "python" in data

    def test_interests_list(self, tmp_path, monkeypatch):
        """Should list interests."""
        self._setup(tmp_path, monkeypatch)
        main(['interests', 'add', '--name', 'test', '-k', 'test'], standalone_mode=False)
        # List should succeed without error
        main(['interests', 'list'], standalone_mode=False)

    def test_interests_remove(self, tmp_path, monkeypatch):
        """Should remove an interest."""
        self._setup(tmp_path, monkeypatch)
        main(['interests', 'add', '--name', 'temp', '-k', 'temp'], standalone_mode=False)
        main(['interests', 'remove', 'temp'], standalone_mode=False)
        with open(tmp_path / ".personal_index" / "interests.json") as f:
            data = json.load(f)
        assert "temp" not in data


class TestCLIPipeline:
    """Test the 'pipeline' command."""

    def _setup(self, tmp_path, monkeypatch):
        """Set up a fresh project with interests."""
        monkeypatch.chdir(tmp_path)
        main(['init'], standalone_mode=False)
        main(['interests', 'add', '--name', 'tech', '-k', 'technology', '-k', 'software'],
             standalone_mode=False)

    def test_pipeline_import_file(self, tmp_path, monkeypatch):
        """Pipeline should import and index a local file."""
        self._setup(tmp_path, monkeypatch)

        # Create a test file
        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Software technology is advancing rapidly. "
            "Modern technology enables new possibilities in software development. "
            "The technology industry continues to grow and innovate."
        )

        main(['pipeline', '--import-file', str(test_file)], standalone_mode=False)

        # Verify index was created
        index_path = tmp_path / ".personal_index" / "search_index.json"
        assert index_path.exists()
        with open(index_path) as f:
            data = json.load(f)
        assert len(data.get("pages", {})) >= 1

    def test_pipeline_multiple_files(self, tmp_path, monkeypatch):
        """Pipeline should handle multiple files."""
        self._setup(tmp_path, monkeypatch)

        for i in range(3):
            f = tmp_path / f"article_{i}.txt"
            f.write_text(f"Article {i} about technology and software development.")

        files = [str(tmp_path / f"article_{i}.txt") for i in range(3)]
        args = ['pipeline']
        for f in files:
            args.extend(['--import-file', f])
        main(args, standalone_mode=False)

        index_path = tmp_path / ".personal_index" / "search_index.json"
        with open(index_path) as f:
            data = json.load(f)
        assert len(data.get("pages", {})) >= 1


class CLISearchTest:
    """Test the 'search' command."""

    def _setup(self, tmp_path, monkeypatch):
        """Set up a project with indexed content."""
        monkeypatch.chdir(tmp_path)
        main(['init'], standalone_mode=False)
        main(['interests', 'add', '--name', 'python', '-k', 'python'], standalone_mode=False)

        # Create and index a file
        test_file = tmp_path / "search_test.txt"
        test_file.write_text(
            "Python programming is a popular language. "
            "Many developers use Python for web development and data science."
        )
        main(['pipeline', '--import-file', str(test_file)], standalone_mode=False)

    def test_search_finds_content(self, tmp_path, monkeypatch, capsys):
        """Search should find indexed content."""
        self._setup(tmp_path, monkeypatch)
        main(['search', 'python'], standalone_mode=False)
        captured = capsys.readouterr()
        assert "python" in captured.out.lower() or "Python" in captured.out

    def test_search_json_format(self, tmp_path, monkeypatch, capsys):
        """Search should support JSON output format."""
        self._setup(tmp_path, monkeypatch)
        main(['search', 'python', '--format', 'json'], standalone_mode=False)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "results" in data
        assert "total" in data

    def test_search_csv_format(self, tmp_path, monkeypatch, capsys):
        """Search should support CSV output format."""
        self._setup(tmp_path, monkeypatch)
        main(['search', 'python', '--format', 'csv'], standalone_mode=False)
        captured = capsys.readouterr()
        assert "title" in captured.out.lower()  # CSV header


class TestCLIDoctor:
    """Test the 'doctor' command."""

    def test_doctor_with_init(self, tmp_path, monkeypatch, capsys):
        """Doctor should report healthy after init."""
        monkeypatch.chdir(tmp_path)
        main(['init'], standalone_mode=False)
        main(['doctor'], standalone_mode=False)
        captured = capsys.readouterr()
        assert "Health Check" in captured.out or "health" in captured.out.lower()


class TestCLIConfig:
    """Test the 'config' command group."""

    def test_config_show(self, tmp_path, monkeypatch, capsys):
        """config show should display current settings."""
        monkeypatch.chdir(tmp_path)
        main(['init'], standalone_mode=False)
        main(['config', 'show'], standalone_mode=False)
        captured = capsys.readouterr()
        assert "Current configuration" in captured.out or "crawler" in captured.out.lower()
