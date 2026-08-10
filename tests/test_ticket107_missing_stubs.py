"""Tests for TICKET-107: Add missing stubs for external libraries."""

from __future__ import annotations

import subprocess
import sys

import pytest


class TestTicket107MissingStubs:
    """Verify mypy missing stubs errors are resolved."""

    def test_mypy_no_missing_stubs_for_defusedxml(self):
        """mypy should not report missing stubs for defusedxml."""
        result = subprocess.run(
            [sys.executable, "-m", "mypy",
             "personal_index/sitemap.py",
             "personal_index/rss.py",
             "--no-error-summary"],
            capture_output=True,
            text=True,
        )
        assert "defusedxml" not in result.stdout or "stub" not in result.stdout, (
            f"defusedxml stub errors found:\n{result.stdout}"
        )

    def test_mypy_no_missing_stubs_for_requests(self):
        """mypy should not report missing stubs for requests."""
        result = subprocess.run(
            [sys.executable, "-m", "mypy",
             "personal_index/content_health.py",
             "personal_index/crawler/__init__.py",
             "personal_index/crawler/main.py",
             "--no-error-summary"],
            capture_output=True,
            text=True,
        )
        assert "requests" not in result.stdout or "stub" not in result.stdout, (
            f"requests stub errors found:\n{result.stdout}"
        )

    def test_mypy_no_missing_stubs_for_yaml(self):
        """mypy should not report missing stubs for yaml."""
        result = subprocess.run(
            [sys.executable, "-m", "mypy",
             "personal_index/config/loader.py",
             "--no-error-summary"],
            capture_output=True,
            text=True,
        )
        assert "yaml" not in result.stdout or "stub" not in result.stdout, (
            f"yaml stub errors found:\n{result.stdout}"
        )

    def test_mypy_config_exists(self):
        """pyproject.toml should have [tool.mypy] section."""
        with open("pyproject.toml") as f:
            content = f.read()
        assert "[tool.mypy]" in content, "Missing [tool.mypy] section in pyproject.toml"

    def test_mypy_config_ignores_defusedxml(self):
        """mypy config should ignore missing imports for defusedxml."""
        with open("pyproject.toml") as f:
            content = f.read()
        assert "defusedxml" in content, "defusedxml not in mypy config"

    def test_mypy_config_ignores_requests(self):
        """mypy config should ignore missing imports for requests."""
        with open("pyproject.toml") as f:
            content = f.read()
        assert "requests" in content, "requests not in mypy config"

    def test_mypy_config_ignores_yaml(self):
        """mypy config should ignore missing imports for yaml."""
        with open("pyproject.toml") as f:
            content = f.read()
        assert "yaml" in content, "yaml not in mypy config"

    def test_mypy_config_ignores_bs4(self):
        """mypy config should ignore missing imports for bs4."""
        with open("pyproject.toml") as f:
            content = f.read()
        assert "bs4" in content, "bs4 not in mypy config"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
