"""End-to-end CLI tests for interests management."""

from __future__ import annotations

import os

import pytest
from click.testing import CliRunner

from personal_index.cli import main
from personal_index.interests import InterestStore


class TestCLIInterestsE2E:
    """Test interests CLI commands end-to-end."""

    def test_interests_add_list_remove(self, tmp_path, monkeypatch):
        """Test full interests lifecycle."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Add interest
        result = runner.invoke(main, [
            "interests", "add", "python",
            "-k", "python", "-k", "django",
        ])
        assert result.exit_code == 0

        # List interests
        result = runner.invoke(main, ["interests", "list"])
        assert result.exit_code == 0
        assert "python" in result.output.lower()

        # Remove interest
        result = runner.invoke(main, ["interests", "remove", "python"])
        assert result.exit_code == 0

        # Verify removed
        result = runner.invoke(main, ["interests", "list"])
        assert "python" not in result.output.lower()

    def test_interests_add_multiple(self, tmp_path, monkeypatch):
        """Test adding multiple interests."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        for name in ["python", "javascript", "rust"]:
            result = runner.invoke(main, [
                "interests", "add", name, "-k", name,
            ])
            assert result.exit_code == 0

        result = runner.invoke(main, ["interests", "list"])
        assert result.exit_code == 0
        for name in ["python", "javascript", "rust"]:
            assert name in result.output.lower()

    def test_interests_persistence(self, tmp_path, monkeypatch):
        """Test interests persist across CLI invocations."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, [
            "interests", "add", "test", "-k", "test",
        ])

        # Verify persistence via InterestStore
        store = InterestStore(
            store_path=os.path.join(".personal_index", "interests.json")
        )
        interests = store.list_all()
        assert any(i.name == "test" for i in interests)

    def test_interests_toggle(self, tmp_path, monkeypatch):
        """Test toggling interest enabled state."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["interests", "add", "test", "-k", "test"])

        result = runner.invoke(main, ["interests", "toggle", "test"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["interests", "list"])
        assert "test" in result.output.lower()
