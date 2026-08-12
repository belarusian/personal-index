"""Tests for cli_verify.py — verify command."""

from __future__ import annotations

import os

from click.testing import CliRunner

from personal_index.cli_verify import verify


class TestVerifyQuick:
    """Tests for quick verification mode."""

    def test_quick_verify_passes(self, tmp_path):
        """Quick verify should pass all component checks."""
        runner = CliRunner()
        result = runner.invoke(verify, ["--data-dir", str(tmp_path), "--quick"])
        assert result.exit_code == 0
        assert "All checks passed" in result.output
        assert "Data directory is writable" in result.output
        assert "Interest store works" in result.output
        assert "Tag store works" in result.output
        assert "Search index works" in result.output
        assert "Content filter works" in result.output
        assert "Content scorer works" in result.output

    def test_quick_verify_skips_pipeline(self, tmp_path):
        """Quick mode should skip the full pipeline test."""
        runner = CliRunner()
        result = runner.invoke(verify, ["--data-dir", str(tmp_path), "--quick"])
        assert result.exit_code == 0
        assert "Running full pipeline self-test" not in result.output

    def test_quick_verify_cleanup(self, tmp_path):
        """Verify should clean up temporary verify files."""
        runner = CliRunner()
        result = runner.invoke(verify, ["--data-dir", str(tmp_path), "--quick"])
        assert result.exit_code == 0
        # Verify temp files should be cleaned up
        assert not os.path.exists(os.path.join(str(tmp_path), "verify_interests.json"))
        assert not os.path.exists(os.path.join(str(tmp_path), "verify_tags.json"))
        assert not os.path.exists(os.path.join(str(tmp_path), "verify_index.json"))


class TestVerifyFull:
    """Tests for full verification mode."""

    def test_full_verify_passes(self, tmp_path):
        """Full verify should pass all checks including pipeline test."""
        runner = CliRunner()
        result = runner.invoke(verify, ["--data-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "All checks passed" in result.output
        assert "Running full pipeline self-test" in result.output
        assert "Full pipeline: all stages" in result.output

    def test_full_verify_pipeline_cleanup(self, tmp_path):
        """Full verify should clean up pipeline test directory."""
        runner = CliRunner()
        result = runner.invoke(verify, ["--data-dir", str(tmp_path)])
        assert result.exit_code == 0
        # Pipeline test directory should be cleaned up
        assert not os.path.exists(os.path.join(str(tmp_path), ".verify_pipeline"))

    def test_full_verify_shows_check_count(self, tmp_path):
        """Verify should show the number of checks passed."""
        runner = CliRunner()
        result = runner.invoke(verify, ["--data-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "checks passed" in result.output
