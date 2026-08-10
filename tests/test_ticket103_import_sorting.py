"""Tests for TICKET-103: Sort imports in multiple modules."""

from __future__ import annotations

import ast
import os
import subprocess
import sys


def _read_file(path: str) -> str:
    """Read file content."""
    base = os.path.join(os.path.dirname(__file__), "..")
    with open(os.path.join(base, path), "r") as f:
        return f.read()


def _docstring_before_future_imports(path: str) -> bool:
    """Check that the module docstring comes before __future__ imports."""
    content = _read_file(path)
    tree = ast.parse(content)

    if not tree.body:
        return True

    first_stmt = tree.body[0]

    if isinstance(first_stmt, ast.Expr) and isinstance(first_stmt.value, ast.Constant) and isinstance(first_stmt.value.value, str):
        return True

    return False


def _ruff_check_i001(path: str) -> bool:
    """Check if ruff reports I001 (unsorted imports) for the file."""
    base = os.path.join(os.path.dirname(__file__), "..")
    full_path = os.path.join(base, path)
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", full_path, "--select", "I001"],
        capture_output=True,
        text=True,
    )
    # Return True if clean (no I001 errors)
    return result.returncode == 0


class TestImportSorting:
    """Verify imports are properly sorted with docstrings first."""

    def test_detector_docstring_first(self):
        """content_tagger/detector.py should have docstring before __future__ imports."""
        assert _docstring_before_future_imports("personal_index/content_tagger/detector.py"), (
            "content_tagger/detector.py docstring should be the first statement"
        )

    def test_importer_docstring_first(self):
        """importer.py should have docstring before __future__ imports."""
        assert _docstring_before_future_imports("personal_index/importer.py"), (
            "importer.py docstring should be the first statement"
        )

    def test_sitemap_docstring_first(self):
        """sitemap.py should have docstring before __future__ imports."""
        assert _docstring_before_future_imports("personal_index/sitemap.py"), (
            "sitemap.py docstring should be the first statement"
        )

    def test_detector_no_i001(self):
        """content_tagger/detector.py should have no ruff I001 violations."""
        assert _ruff_check_i001("personal_index/content_tagger/detector.py"), (
            "content_tagger/detector.py has unsorted imports (I001)"
        )

    def test_importer_no_i001(self):
        """importer.py should have no ruff I001 violations."""
        assert _ruff_check_i001("personal_index/importer.py"), (
            "importer.py has unsorted imports (I001)"
        )

    def test_sitemap_no_i001(self):
        """sitemap.py should have no ruff I001 violations."""
        assert _ruff_check_i001("personal_index/sitemap.py"), (
            "sitemap.py has unsorted imports (I001)"
        )
