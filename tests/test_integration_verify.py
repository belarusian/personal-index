"""Integration tests for the verify command."""

from __future__ import annotations

from click.testing import CliRunner

from personal_index.cli import main


class TestVerifyCommand:
    """Test the verify command."""

    def test_verify_quick(self, tmp_path, monkeypatch):
        """Test quick verification mode."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        result = runner.invoke(main, ["verify", "--quick"])
        assert result.exit_code == 0

    def test_verify_full(self, tmp_path, monkeypatch):
        """Test full verification mode."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        result = runner.invoke(main, ["verify"])
        assert result.exit_code == 0
        assert "checks passed" in result.output.lower() or "All checks passed" in result.output

    def test_verify_without_init(self, tmp_path, monkeypatch):
        """Test verify without prior init."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(main, ["verify", "--quick"])
        # Should still work, creating data dir as needed
        assert result.exit_code == 0
