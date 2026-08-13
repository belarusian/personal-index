#!/usr/bin/env python3
"""Tests for personal_index.publish_dashboard."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from personal_index import publish_dashboard


class TestRun:
    """Tests for publish_dashboard.run()."""

    def test_run_success(self):
        """run() returns CompletedProcess on success."""
        mock_result = MagicMock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 0
        mock_result.stdout = "output\n"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_subprocess:
            result = publish_dashboard.run(["echo", "hello"])
            assert result is mock_result
            mock_subprocess.assert_called_once_with(
                ["echo", "hello"],
                capture_output=True,
                text=True,
                cwd=None,
                check=False,
            )

    def test_run_with_cwd(self):
        """run() passes cwd to subprocess."""
        mock_result = MagicMock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        cwd = Path("/tmp/test")
        with patch("subprocess.run", return_value=mock_result) as mock_subprocess:
            publish_dashboard.run(["ls"], cwd=cwd)
            mock_subprocess.assert_called_once()
            call_kwargs = mock_subprocess.call_args[1]
            assert call_kwargs["cwd"] == cwd

    def test_run_failure_exits(self):
        """run() calls sys.exit(1) on failure when check=True."""
        mock_result = MagicMock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error\n"

        with patch("subprocess.run", return_value=mock_result):
            with patch.object(publish_dashboard.sys, "exit") as mock_exit:
                mock_exit.side_effect = SystemExit(1)
                with pytest.raises(SystemExit):
                    publish_dashboard.run(["false"], check=True)
                mock_exit.assert_called_once_with(1)

    def test_run_failure_no_check(self):
        """run() does not exit when check=False."""
        mock_result = MagicMock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error\n"

        with patch("subprocess.run", return_value=mock_result):
            with patch.object(publish_dashboard.sys, "exit") as mock_exit:
                publish_dashboard.run(["false"], check=False)
                mock_exit.assert_not_called()


class TestRegenerate:
    """Tests for publish_dashboard.regenerate()."""

    def test_regenerate_success(self, tmp_path):
        """regenerate() returns paths when files exist."""
        html = tmp_path / "personal_index" / "docs_dashboard.html"
        json_path = tmp_path / "personal_index" / "docs_dashboard_metadata.json"
        html.parent.mkdir(parents=True, exist_ok=True)
        html.write_text("<html></html>")
        json_path.write_text("{}")

        with patch.object(publish_dashboard, "run") as mock_run:
            mock_result = MagicMock(spec=subprocess.CompletedProcess)
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            result_html, result_json = publish_dashboard.regenerate(tmp_path)
            assert result_html == html
            assert result_json == json_path

    def test_regenerate_missing_html(self, tmp_path):
        """regenerate() exits when HTML file is missing."""
        json_path = tmp_path / "personal_index" / "docs_dashboard_metadata.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text("{}")

        with patch.object(publish_dashboard, "run") as mock_run:
            mock_result = MagicMock(spec=subprocess.CompletedProcess)
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            with patch.object(publish_dashboard.sys, "exit") as mock_exit:
                mock_exit.side_effect = SystemExit(1)
                with pytest.raises(SystemExit):
                    publish_dashboard.regenerate(tmp_path)
                mock_exit.assert_called_once_with(1)

    def test_regenerate_missing_json(self, tmp_path):
        """regenerate() exits when JSON file is missing."""
        html = tmp_path / "personal_index" / "docs_dashboard.html"
        html.parent.mkdir(parents=True, exist_ok=True)
        html.write_text("<html></html>")

        with patch.object(publish_dashboard, "run") as mock_run:
            mock_result = MagicMock(spec=subprocess.CompletedProcess)
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            with patch.object(publish_dashboard.sys, "exit") as mock_exit:
                mock_exit.side_effect = SystemExit(1)
                with pytest.raises(SystemExit):
                    publish_dashboard.regenerate(tmp_path)
                mock_exit.assert_called_once_with(1)


class TestValidateSync:
    """Tests for publish_dashboard.validate_sync()."""

    def _make_synced_files(self, tmp_path):
        """Create matching HTML and JSON files."""
        summary = {"total_modules": 5, "total_errors": 0, "total_warnings": 0}
        codemap = {"summary": summary}
        json_path = tmp_path / "codemap.json"
        json_path.write_text(json.dumps(codemap))

        html_content = (
            '<script type="application/json" id="codemap-metadata">'
            + json.dumps({"summary": summary})
            + "</script>"
        )
        html_path = tmp_path / "dashboard.html"
        html_path.write_text(html_content)
        return html_path, json_path

    def test_validate_sync_ok(self, tmp_path):
        """validate_sync returns sync=True when files match."""
        html_path, json_path = self._make_synced_files(tmp_path)
        result = publish_dashboard.validate_sync(html_path, json_path)
        assert result["sync"] is True
        assert result["summary"]["total_modules"] == 5

    def test_validate_sync_mismatch(self, tmp_path):
        """validate_sync returns sync=False when files differ."""
        json_path = tmp_path / "codemap.json"
        json_path.write_text(json.dumps({"summary": {"total_modules": 5}}))

        html_path = tmp_path / "dashboard.html"
        html_path.write_text(
            '<script type="application/json" id="codemap-metadata">'
            + json.dumps({"summary": {"total_modules": 3}})
            + "</script>"
        )

        result = publish_dashboard.validate_sync(html_path, json_path)
        assert result["sync"] is False
        assert "mismatches" in result

    def test_validate_sync_no_metadata(self, tmp_path):
        """validate_sync returns sync=False when no embedded metadata."""
        json_path = tmp_path / "codemap.json"
        json_path.write_text(json.dumps({"summary": {"total_modules": 5}}))

        html_path = tmp_path / "dashboard.html"
        html_path.write_text("<html><body>No metadata</body></html>")

        result = publish_dashboard.validate_sync(html_path, json_path)
        assert result["sync"] is False
        assert result["reason"] == "no embedded metadata"


class TestPublish:
    """Tests for publish_dashboard.publish()."""

    def test_publish_dry_run(self, tmp_path):
        """publish() skips file ops in dry_run mode."""
        html = tmp_path / "html" / "dashboard.html"
        json_path = tmp_path / "html" / "codemap.json"
        html.parent.mkdir(parents=True, exist_ok=True)
        html.write_text("<html></html>")
        json_path.write_text("{}")

        search_repo = tmp_path / "search"
        search_repo.mkdir()

        with patch.object(publish_dashboard, "run") as mock_run:
            mock_result = MagicMock(spec=subprocess.CompletedProcess)
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            publish_dashboard.publish(html, json_path, search_repo, dry_run=True)
            # In dry run, no git operations should be called
            assert not any(
                call for call in mock_run.call_args_list
                if "git" in str(call)
            )

    def test_publish_missing_repo(self, tmp_path):
        """publish() exits when search repo doesn't exist."""
        html = tmp_path / "dashboard.html"
        html.write_text("<html></html>")
        json_path = tmp_path / "codemap.json"
        json_path.write_text("{}")

        with patch.object(publish_dashboard.sys, "exit") as mock_exit:
            mock_exit.side_effect = SystemExit(1)
            with pytest.raises(SystemExit):
                publish_dashboard.publish(html, json_path, tmp_path / "nonexistent", dry_run=False)
            mock_exit.assert_called_once_with(1)

    def test_publish_no_changes(self, tmp_path):
        """publish() returns early when git diff --cached is clean."""
        html = tmp_path / "html" / "dashboard.html"
        json_path = tmp_path / "html" / "codemap.json"
        html.parent.mkdir(parents=True, exist_ok=True)
        html.write_text("<html></html>")
        json_path.write_text(json.dumps({"summary": {"total_modules": 1}}))

        search_repo = tmp_path / "search"
        search_repo.mkdir()

        with patch.object(publish_dashboard, "run") as mock_run:
            mock_result = MagicMock(spec=subprocess.CompletedProcess)
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            publish_dashboard.publish(html, json_path, search_repo, dry_run=False)
            # Should have called git add and git diff --cached
            calls = [str(c) for c in mock_run.call_args_list]
            assert any("git" in c for c in calls)
