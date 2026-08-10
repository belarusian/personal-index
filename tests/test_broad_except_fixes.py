"""Tests verifying broad 'except Exception' catches have been narrowed."""

from __future__ import annotations

import ast
import os
from pathlib import Path


def _get_except_handlers(filepath: str) -> list[str]:
    """Parse a Python file and return all except handler exception types."""
    with open(filepath, "r") as f:
        tree = ast.parse(f.read())

    handlers = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                handlers.append("bare-except")
            elif isinstance(node.type, ast.Name):
                handlers.append(node.type.id)
            elif isinstance(node.type, ast.Tuple):
                names = []
                for elt in node.type.elts:
                    if isinstance(elt, ast.Attribute):
                        # e.g. sqlite3.Error
                        parts = []
                        n = elt
                        while isinstance(n, ast.Attribute):
                            parts.append(n.attr)
                            n = n.value
                        if isinstance(n, ast.Name):
                            parts.append(n.id)
                        names.append(".".join(reversed(parts)))
                    elif isinstance(elt, ast.Name):
                        names.append(elt.id)
                handlers.append(",".join(names))
    return handlers


class TestNoBroadExceptInMigrationsBase:
    """migrations/base.py should not catch bare Exception."""

    def test_no_broad_exception(self):
        filepath = Path("personal_index/migrations/base.py")
        handlers = _get_except_handlers(str(filepath))
        assert "Exception" not in handlers, (
            f"migrations/base.py still catches broad Exception: {handlers}"
        )

    def test_narrowed_to_specific_types(self):
        filepath = Path("personal_index/migrations/base.py")
        handlers = _get_except_handlers(str(filepath))
        # Should have specific types like ImportError, OSError, etc.
        assert any("ImportError" in h for h in handlers), (
            f"Expected ImportError in handlers: {handlers}"
        )


class TestNoBroadExceptInContentHealth:
    """content_health.py should not catch bare Exception."""

    def test_no_broad_exception(self):
        filepath = Path("personal_index/content_health.py")
        handlers = _get_except_handlers(str(filepath))
        assert "Exception" not in handlers, (
            f"content_health.py still catches broad Exception: {handlers}"
        )

    def test_database_check_narrowed(self):
        filepath = Path("personal_index/content_health.py")
        handlers = _get_except_handlers(str(filepath))
        # Should have sqlite3.Error or similar
        assert any("sqlite3" in h for h in handlers), (
            f"Expected sqlite3.Error in handlers: {handlers}"
        )


class TestNoBroadExceptInPipeline:
    """pipeline.py should not catch bare Exception."""

    def test_no_broad_exception(self):
        filepath = Path("personal_index/pipeline.py")
        handlers = _get_except_handlers(str(filepath))
        assert "Exception" not in handlers, (
            f"pipeline.py still catches broad Exception: {handlers}"
        )

    def test_narrowed_to_value_type_runtime(self):
        filepath = Path("personal_index/pipeline.py")
        handlers = _get_except_handlers(str(filepath))
        assert any("ValueError" in h for h in handlers), (
            f"Expected ValueError in handlers: {handlers}"
        )


class TestNoBroadExceptInExportMarkdown:
    """export_markdown.py should not catch bare Exception."""

    def test_no_broad_exception(self):
        filepath = Path("personal_index/export_markdown.py")
        handlers = _get_except_handlers(str(filepath))
        assert "Exception" not in handlers, (
            f"export_markdown.py still catches broad Exception: {handlers}"
        )

    def test_narrowed_to_os_io_value(self):
        filepath = Path("personal_index/export_markdown.py")
        handlers = _get_except_handlers(str(filepath))
        assert any("OSError" in h for h in handlers), (
            f"Expected OSError in handlers: {handlers}"
        )
