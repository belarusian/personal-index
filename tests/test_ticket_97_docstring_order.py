"""Test that module docstrings come before imports (TICKET-97)."""

import ast
import importlib
from pathlib import Path

FILES_WITH_CLASSVAR = [
    "personal_index/bookmark_export.py",
    "personal_index/content_categorizer.py",
    "personal_index/content_enricher.py",
    "personal_index/content_tagger/detector.py",
    "personal_index/encoding.py",
    "personal_index/export.py",
    "personal_index/importer.py",
    "personal_index/sitemap.py",
    "personal_index/url_classifier.py",
    "personal_index/validator.py",
]


def _get_first_statement(filepath: str) -> ast.stmt:
    """Parse file and return the first non-future import statement."""
    with open(filepath) as f:
        tree = ast.parse(f.read())
    # Skip __future__ imports (they must be first)
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            continue
        return node
    return tree.body[0] if tree.body else None


def _get_docstring_node(filepath: str) -> ast.Expr | None:
    """Find the module-level docstring node."""
    with open(filepath) as f:
        tree = ast.parse(f.read())
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, (ast.Constant, ast.Str)):
            val = node.value.value if isinstance(node.value, ast.Constant) else node.value.s
            if isinstance(val, str) and len(val) > 20:  # reasonable docstring length
                return node
    return None


class TestDocstringBeforeImports:
    """Verify module docstrings appear before regular imports (PEP 257)."""

    def test_all_files_have_docstring(self):
        """All affected files should have a module docstring."""
        for filepath in FILES_WITH_CLASSVAR:
            docstring_node = _get_docstring_node(filepath)
            assert docstring_node is not None, f"{filepath} has no module docstring"

    def test_docstring_before_classvar_import(self):
        """Docstring should appear before `from typing import ClassVar`."""
        for filepath in FILES_WITH_CLASSVAR:
            with open(filepath) as f:
                tree = ast.parse(f.read())
            
            docstring_line = None
            classvar_line = None
            
            for node in tree.body:
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                    if isinstance(node.value.value, str) and len(node.value.value) > 20:
                        docstring_line = node.lineno
                if isinstance(node, ast.ImportFrom) and node.module == "typing":
                    for alias in node.names:
                        if alias.name == "ClassVar":
                            classvar_line = node.lineno
            
            assert docstring_line is not None, f"{filepath}: no docstring found"
            assert classvar_line is not None, f"{filepath}: no ClassVar import found"
            assert docstring_line < classvar_line, (
                f"{filepath}: docstring at line {docstring_line} should come "
                f"before ClassVar import at line {classvar_line}"
            )

    def test_modules_importable(self):
        """All affected modules should be importable after the fix."""
        for filepath in FILES_WITH_CLASSVAR:
            module_name = filepath.replace("/", ".").replace(".py", "")
            mod = importlib.import_module(module_name)
            assert mod is not None
            # Verify docstring is accessible
            assert mod.__doc__ is not None, f"{module_name}: __doc__ is None"
            assert len(mod.__doc__) > 20, f"{module_name}: docstring too short"
