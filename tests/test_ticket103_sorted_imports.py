"""Tests for TICKET-103: Sort imports in multiple modules."""

from __future__ import annotations

import ast
import subprocess
import sys

import pytest


def _get_imports(filepath: str) -> list[tuple[str, str]]:
    """Parse imports from a file and return (module, names) tuples."""
    with open(filepath) as f:
        tree = ast.parse(f.read())
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                imports.append((node.module, alias.name))
    return imports


class TestTicket103SortedImports:
    """Verify import sorting fixes in multiple modules."""

    def test_importer_defusedxml_imports_present(self):
        """importer.py should have defusedxml imports for both ParseError and fromstring."""
        with open("personal_index/importer.py") as f:
            source = f.read()
        assert "ParseError as ET_ParseError" in source
        assert "fromstring as ET_fromstring" in source

    def test_sitemap_defusedxml_imports_present(self):
        """sitemap.py should have defusedxml imports for both ParseError and fromstring."""
        with open("personal_index/sitemap.py") as f:
            source = f.read()
        assert "ParseError as ET_ParseError" in source
        assert "fromstring as ET_fromstring" in source

    def test_importer_imports_work(self):
        """importer.py imports should still work after sorting."""
        from personal_index.importer import Importer, ImportResult
        assert Importer is not None
        assert ImportResult is not None

    def test_sitemap_imports_work(self):
        """sitemap.py imports should still work after sorting."""
        from personal_index.sitemap import Sitemap, SitemapParser
        assert SitemapParser is not None
        assert Sitemap is not None

    def test_ruff_no_import_sorting_errors(self):
        """ruff should report no I001 import sorting errors."""
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check",
             "personal_index/content_tagger/detector.py",
             "personal_index/importer.py",
             "personal_index/sitemap.py",
             "--select", "I"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"ruff found import sorting errors:\n{result.stdout}\n{result.stderr}"

    def test_detector_imports_sorted(self):
        """detector.py imports should be properly sorted."""
        imports = _get_imports("personal_index/content_tagger/detector.py")
        modules = [m for m, _ in imports]
        # Verify stdlib imports come before local imports
        local_idx = None
        stdlib_idx = None
        for i, m in enumerate(modules):
            if m.startswith("personal_index"):
                local_idx = i
                break
            if m in ("__future__", "re", "dataclasses", "typing"):
                stdlib_idx = i
        if local_idx is not None and stdlib_idx is not None:
            assert stdlib_idx < local_idx, "stdlib imports should come before local imports"

    def test_importer_imports_sorted(self):
        """importer.py imports should be properly sorted."""
        imports = _get_imports("personal_index/importer.py")
        modules = [m for m, _ in imports]
        # Verify stdlib imports come before third-party, which come before local
        local_idx = None
        third_party_idx = None
        for i, m in enumerate(modules):
            if m.startswith("."):
                local_idx = i
                break
            if m.startswith("defusedxml"):
                third_party_idx = i
        if local_idx is not None and third_party_idx is not None:
            assert third_party_idx < local_idx, "third-party imports should come before local imports"

    def test_sitemap_imports_sorted(self):
        """sitemap.py imports should be properly sorted."""
        imports = _get_imports("personal_index/sitemap.py")
        modules = [m for m, _ in imports]
        # Verify stdlib imports come before third-party
        third_party_idx = None
        stdlib_idx = None
        for i, m in enumerate(modules):
            if m.startswith("defusedxml"):
                third_party_idx = i
                break
            if m in ("__future__", "contextlib", "dataclasses", "datetime", "typing",
                     "urllib.parse", "xml.etree.ElementTree"):
                stdlib_idx = i
        if third_party_idx is not None and stdlib_idx is not None:
            assert stdlib_idx < third_party_idx, "stdlib imports should come before third-party imports"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
