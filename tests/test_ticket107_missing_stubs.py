"""Tests for TICKET-107: Add missing stubs for external libraries."""

from __future__ import annotations

import subprocess
import sys

import pytest


def _check_mypy_stubs(paths: list[str]) -> list[str]:
    """Run mypy on given files and return stub/import-untyped errors."""
    result = subprocess.run(
        [sys.executable, "-m", "mypy"] + paths + ["--no-error-summary"],
        capture_output=True,
        text=True,
    )
    errors = [
        line for line in result.stdout.split("\n")
        if "import-untyped" in line or "Library stubs not installed" in line
    ]
    return errors


class TestTicket107MissingStubs:
    """Verify type stubs are installed for external libraries."""

    def test_sitemap_no_stub_errors(self):
        """sitemap.py should have no stub/import-untyped errors."""
        errors = _check_mypy_stubs(["personal_index/sitemap.py"])
        assert not errors, f"sitemap.py has stub errors:\n" + "\n".join(errors)

    def test_rss_no_stub_errors(self):
        """rss.py should have no stub/import-untyped errors."""
        errors = _check_mypy_stubs(["personal_index/rss.py"])
        assert not errors, f"rss.py has stub errors:\n" + "\n".join(errors)

    def test_content_health_no_stub_errors(self):
        """content_health.py should have no stub/import-untyped errors."""
        errors = _check_mypy_stubs(["personal_index/content_health.py"])
        assert not errors, f"content_health.py has stub errors:\n" + "\n".join(errors)

    def test_crawler_init_no_stub_errors(self):
        """crawler/__init__.py should have no stub/import-untyped errors."""
        errors = _check_mypy_stubs(["personal_index/crawler/__init__.py"])
        assert not errors, f"crawler/__init__.py has stub errors:\n" + "\n".join(errors)

    def test_crawler_main_no_stub_errors(self):
        """crawler/main.py should have no stub/import-untyped errors."""
        errors = _check_mypy_stubs(["personal_index/crawler/main.py"])
        assert not errors, f"crawler/main.py has stub errors:\n" + "\n".join(errors)

    def test_config_loader_no_stub_errors(self):
        """config/loader.py should have no stub/import-untyped errors."""
        errors = _check_mypy_stubs(["personal_index/config/loader.py"])
        assert not errors, f"config/loader.py has stub errors:\n" + "\n".join(errors)

    def test_types_requests_installed(self):
        """types-requests package should be installed."""
        import importlib.metadata
        try:
            version = importlib.metadata.version("types-requests")
            assert version, "types-requests should be installed"
        except importlib.metadata.PackageNotFoundError:
            pytest.fail("types-requests package is not installed")

    def test_types_pyyaml_installed(self):
        """types-PyYAML package should be installed."""
        import importlib.metadata
        try:
            version = importlib.metadata.version("types-PyYAML")
            assert version, "types-PyYAML should be installed"
        except importlib.metadata.PackageNotFoundError:
            pytest.fail("types-PyYAML package is not installed")

    def test_types_defusedxml_installed(self):
        """types-defusedxml package should be installed."""
        import importlib.metadata
        try:
            version = importlib.metadata.version("types-defusedxml")
            assert version, "types-defusedxml should be installed"
        except importlib.metadata.PackageNotFoundError:
            pytest.fail("types-defusedxml package is not installed")
