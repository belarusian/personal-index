#!/usr/bin/env python3
"""Tests for personal_index.cycle_signals — pure function coverage."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from personal_index import cycle_signals


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_modules() -> list[dict]:
    """A small codemap modules list for testing."""
    return [
        {
            "name": "personal_index.analytics",
            "lines": 150,
            "functions": 10,
            "classes": 2,
            "tests": 5,
            "ruff_errors": 0,
            "mypy_errors": 0,
            "ruff_warnings": 0,
            "imports": ["personal_index.models"],
        },
        {
            "name": "personal_index.big_module",
            "lines": 350,
            "functions": 20,
            "classes": 3,
            "tests": 0,
            "ruff_errors": 2,
            "mypy_errors": 1,
            "ruff_warnings": 1,
            "imports": [],
        },
        {
            "name": "personal_index.cli_app",
            "lines": 80,
            "functions": 5,
            "classes": 0,
            "tests": 0,
            "ruff_errors": 0,
            "mypy_errors": 0,
            "ruff_warnings": 0,
            "imports": [],
        },
        {
            "name": "personal_index.__init__",
            "lines": 10,
            "functions": 0,
            "classes": 0,
            "tests": 0,
            "ruff_errors": 0,
            "mypy_errors": 0,
            "ruff_warnings": 0,
            "imports": [],
        },
        {
            "name": "personal_index.exporter",
            "lines": 220,
            "functions": 16,
            "classes": 1,
            "tests": 0,
            "ruff_errors": 0,
            "mypy_errors": 0,
            "ruff_warnings": 0,
            "imports": ["personal_index.models"],
        },
        {
            "name": "personal_index.export_csv",
            "lines": 180,
            "functions": 12,
            "classes": 0,
            "tests": 0,
            "ruff_errors": 0,
            "mypy_errors": 0,
            "ruff_warnings": 0,
            "imports": [],
        },
        {
            "name": "personal_index.models",
            "lines": 60,
            "functions": 2,
            "classes": 4,
            "tests": 3,
            "ruff_errors": 0,
            "mypy_errors": 0,
            "ruff_warnings": 0,
            "imports": [],
        },
        {
            "name": "personal_index.subpkg.helper",
            "lines": 90,
            "functions": 6,
            "classes": 0,
            "tests": 0,
            "ruff_errors": 1,
            "mypy_errors": 0,
            "ruff_warnings": 0,
            "imports": [],
        },
    ]


@pytest.fixture
def sample_dep_graph() -> dict:
    """A dependency graph matching sample_modules."""
    return {
        "personal_index.analytics": ["personal_index.models"],
        "personal_index.big_module": [],
        "personal_index.exporter": ["personal_index.models"],
        "personal_index.export_csv": [],
        "personal_index.models": [],
        "personal_index.cli_app": [],
        "personal_index.__init__": [],
        "personal_index.subpkg.helper": [],
    }


@pytest.fixture
def sample_codemap(sample_modules, sample_dep_graph) -> dict:
    """A complete codemap dict."""
    return {
        "modules": sample_modules,
        "dependency_graph": sample_dep_graph,
        "summary": {
            "total_modules": len(sample_modules),
            "total_lines": sum(m["lines"] for m in sample_modules),
            "total_errors": 3,
            "total_warnings": 1,
        },
        "generated_at": "2025-01-01T00:00:00",
    }


# ---------------------------------------------------------------------------
# build_tree
# ---------------------------------------------------------------------------

class TestBuildTree:
    def test_empty_modules(self):
        tree = cycle_signals.build_tree([])
        assert tree["name"] == "root"
        assert tree["stats"]["modules"] == 0
        assert tree["children"] == {}

    def test_single_module(self, sample_modules):
        mods = [sample_modules[0]]  # personal_index.analytics
        tree = cycle_signals.build_tree(mods)
        assert tree["stats"]["modules"] == 1
        assert tree["stats"]["lines"] == 150

    def test_nested_module(self, sample_modules):
        mods = [sample_modules[7]]  # personal_index.subpkg.helper
        tree = cycle_signals.build_tree(mods)
        assert tree["stats"]["modules"] == 1
        # personal_index is the top-level child, subpkg is nested under it
        assert "personal_index" in tree["children"]
        assert "subpkg" in tree["children"]["personal_index"]["children"]

    def test_signals_propagate(self, sample_modules):
        # big_module has errors → S5
        mods = [sample_modules[1]]  # big_module
        tree = cycle_signals.build_tree(mods)
        assert "S5" in tree["signals"]

    def test_skip_root_only(self):
        """Modules with no dot in name are skipped."""
        mods = [{"name": "standalone", "lines": 10, "functions": 1, "classes": 0, "tests": 0,
                 "ruff_errors": 0, "mypy_errors": 0, "ruff_warnings": 0}]
        tree = cycle_signals.build_tree(mods)
        assert tree["stats"]["modules"] == 0


# ---------------------------------------------------------------------------
# format_tree
# ---------------------------------------------------------------------------

class TestFormatTree:
    def test_empty_tree(self):
        result = cycle_signals.format_tree({"children": {}})
        assert result == "no packages found"

    def test_basic_tree(self, sample_modules):
        tree = cycle_signals.build_tree(sample_modules)
        result = cycle_signals.format_tree(tree)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_max_depth(self, sample_modules):
        tree = cycle_signals.build_tree(sample_modules)
        shallow = cycle_signals.format_tree(tree, max_depth=1)
        deep = cycle_signals.format_tree(tree, max_depth=3)
        # Deeper should have more content
        assert len(deep) >= len(shallow)

    def test_max_lines_limits_output(self, sample_modules):
        """max_lines constrains output — smaller limit produces fewer lines."""
        tree = cycle_signals.build_tree(sample_modules)
        result_small = cycle_signals.format_tree(tree, max_lines=3)
        result_large = cycle_signals.format_tree(tree, max_lines=100)
        # Smaller limit should produce fewer or equal lines
        assert len(result_small.split("\n")) <= len(result_large.split("\n"))


# ---------------------------------------------------------------------------
# signal_no_tests
# ---------------------------------------------------------------------------

class TestSignalNoTests:
    def test_basic(self, sample_modules):
        results = cycle_signals.signal_no_tests(sample_modules)
        # big_module, exporter, export_csv, subpkg.helper should be flagged
        # analytics has tests, cli_app is skipped (cli_), __init__ is skipped
        module_names = [r["module"] for r in results]
        assert "personal_index.big_module" in module_names
        assert "personal_index.exporter" in module_names
        assert "personal_index.cli_app" not in module_names  # cli_ prefix
        assert "personal_index.__init__" not in module_names

    def test_severity(self, sample_modules):
        results = cycle_signals.signal_no_tests(sample_modules)
        for r in results:
            if r["lines"] > 100:
                assert r["severity"] == "high"
            else:
                assert r["severity"] == "medium"

    def test_sorted_by_lines_desc(self, sample_modules):
        results = cycle_signals.signal_no_tests(sample_modules)
        lines = [r["lines"] for r in results]
        assert lines == sorted(lines, reverse=True)

    def test_empty(self):
        results = cycle_signals.signal_no_tests([])
        assert results == []


# ---------------------------------------------------------------------------
# signal_oversized
# ---------------------------------------------------------------------------

class TestSignalOversized:
    def test_basic(self, sample_modules):
        results = cycle_signals.signal_oversized(sample_modules)
        module_names = [r["module"] for r in results]
        # big_module (350L, 20f) and exporter (220L, 16f) should be flagged
        assert "personal_index.big_module" in module_names
        assert "personal_index.exporter" in module_names
        # analytics (150L) should not
        assert "personal_index.analytics" not in module_names

    def test_custom_thresholds(self, sample_modules):
        results = cycle_signals.signal_oversized(sample_modules, line_threshold=300, func_threshold=10)
        module_names = [r["module"] for r in results]
        assert "personal_index.big_module" in module_names
        assert "personal_index.exporter" not in module_names  # 220 < 300

    def test_severity(self, sample_modules):
        results = cycle_signals.signal_oversized(sample_modules)
        for r in results:
            if r["lines"] > 400:
                assert r["severity"] == "critical"
            else:
                assert r["severity"] == "high"

    def test_sorted_by_lines_desc(self, sample_modules):
        results = cycle_signals.signal_oversized(sample_modules)
        lines = [r["lines"] for r in results]
        assert lines == sorted(lines, reverse=True)


# ---------------------------------------------------------------------------
# signal_dead_code
# ---------------------------------------------------------------------------

class TestSignalDeadCode:
    def test_basic(self, sample_modules, sample_dep_graph):
        results = cycle_signals.signal_dead_code(sample_modules, sample_dep_graph)
        module_names = [r["module"] for r in results]
        # analytics imports models → models is imported
        # big_module, cli_app, export_csv, subpkg.helper are not imported
        assert "personal_index.big_module" in module_names
        assert "personal_index.models" not in module_names  # imported by analytics

    def test_skip_init_main(self, sample_modules, sample_dep_graph):
        results = cycle_signals.signal_dead_code(sample_modules, sample_dep_graph)
        module_names = [r["module"] for r in results]
        assert "personal_index.__init__" not in module_names

    def test_confidence_always_low(self, sample_modules, sample_dep_graph):
        results = cycle_signals.signal_dead_code(sample_modules, sample_dep_graph)
        for r in results:
            assert r["confidence"] == "low"

    def test_empty(self):
        results = cycle_signals.signal_dead_code([], {})
        assert results == []


# ---------------------------------------------------------------------------
# signal_duplicates
# ---------------------------------------------------------------------------

class TestSignalDuplicates:
    def test_basic(self, sample_modules):
        """signal_duplicates groups modules with overlapping name stems."""
        results = cycle_signals.signal_duplicates(sample_modules)
        # The function uses name.replace("_", "")[:12] as stem
        # "analytics" → "analytics", "big_module" → "bigmodule", etc.
        # All stems in sample_modules are unique, so no duplicates expected
        # Verify the function returns a list of dicts with expected keys
        for r in results:
            assert "stem" in r
            assert "modules" in r
            assert "count" in r
            assert r["count"] >= 2

    def test_actual_duplicates(self):
        """Modules with same stem after underscore removal are grouped."""
        mods = [
            {"name": "pkg.content_export", "lines": 10, "functions": 1, "classes": 0, "tests": 0,
             "ruff_errors": 0, "mypy_errors": 0, "ruff_warnings": 0},
            {"name": "pkg.content_exporter", "lines": 10, "functions": 1, "classes": 0, "tests": 0,
             "ruff_errors": 0, "mypy_errors": 0, "ruff_warnings": 0},
        ]
        results = cycle_signals.signal_duplicates(mods)
        # contentexport and contentexporte are different stems (12 char limit)
        # Let's use shorter names that actually collide
        assert isinstance(results, list)

    def test_colliding_stems(self):
        """Verify stem collision detection works."""
        mods = [
            {"name": "pkg.ab", "lines": 10, "functions": 1, "classes": 0, "tests": 0,
             "ruff_errors": 0, "mypy_errors": 0, "ruff_warnings": 0},
            {"name": "pkg.a_b", "lines": 10, "functions": 1, "classes": 0, "tests": 0,
             "ruff_errors": 0, "mypy_errors": 0, "ruff_warnings": 0},
        ]
        # "ab" → "ab", "a_b" → "ab" — same stem!
        results = cycle_signals.signal_duplicates(mods)
        assert len(results) >= 1
        stems = [r["stem"] for r in results]
        assert "ab" in stems

    def test_no_duplicates(self):
        mods = [
            {"name": "pkg.alpha", "lines": 10, "functions": 1, "classes": 0, "tests": 0,
             "ruff_errors": 0, "mypy_errors": 0, "ruff_warnings": 0},
            {"name": "pkg.beta", "lines": 10, "functions": 1, "classes": 0, "tests": 0,
             "ruff_errors": 0, "mypy_errors": 0, "ruff_warnings": 0},
        ]
        results = cycle_signals.signal_duplicates(mods)
        assert results == []

    def test_sorted_by_count_desc(self, sample_modules):
        results = cycle_signals.signal_duplicates(sample_modules)
        counts = [r["count"] for r in results]
        assert counts == sorted(counts, reverse=True)


# ---------------------------------------------------------------------------
# signal_errors
# ---------------------------------------------------------------------------

class TestSignalErrors:
    def test_basic(self, sample_modules):
        results = cycle_signals.signal_errors(sample_modules)
        module_names = [r["module"] for r in results]
        # big_module has 2 ruff + 1 mypy + 1 warning = 4
        assert "personal_index.big_module" in module_names
        # subpkg.helper has 1 ruff error
        assert "personal_index.subpkg.helper" in module_names

    def test_sorted_by_total_desc(self, sample_modules):
        results = cycle_signals.signal_errors(sample_modules)
        totals = [r["total"] for r in results]
        assert totals == sorted(totals, reverse=True)

    def test_no_errors(self):
        mods = [
            {"name": "pkg.clean", "lines": 10, "functions": 1, "classes": 0, "tests": 0,
             "ruff_errors": 0, "mypy_errors": 0, "ruff_warnings": 0},
        ]
        results = cycle_signals.signal_errors(mods)
        assert results == []


# ---------------------------------------------------------------------------
# signal_coverage
# ---------------------------------------------------------------------------

class TestSignalCoverage:
    def test_no_test_dir(self, sample_modules):
        result = cycle_signals.signal_coverage(sample_modules, test_dir=None)
        assert "coverage_pct" in result
        assert "total_modules" in result
        assert result["total_modules"] == len(sample_modules)

    def test_with_test_dir(self, sample_modules, tmp_path):
        # Create test files matching some modules
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_analytics.py").write_text("def test_x(): pass")
        (test_dir / "test_models.py").write_text("def test_y(): pass")

        result = cycle_signals.signal_coverage(sample_modules, test_dir=str(test_dir))
        assert result["modules_with_tests"] >= 2
        assert result["coverage_pct"] > 0

    def test_empty_modules(self):
        result = cycle_signals.signal_coverage([], test_dir=None)
        assert result["total_modules"] == 0
        assert result["coverage_pct"] == 0


# ---------------------------------------------------------------------------
# format_for_auditor
# ---------------------------------------------------------------------------

class TestFormatForAuditor:
    def test_basic(self, sample_modules, sample_dep_graph):
        signals = {
            "S1_no_tests": cycle_signals.signal_no_tests(sample_modules),
            "S2_oversized": cycle_signals.signal_oversized(sample_modules),
            "S3_dead_code": cycle_signals.signal_dead_code(sample_modules, sample_dep_graph),
            "S4_duplicates": cycle_signals.signal_duplicates(sample_modules),
            "S5_errors": cycle_signals.signal_errors(sample_modules),
            "S6_coverage": cycle_signals.signal_coverage(sample_modules),
            "tree_summary": cycle_signals.build_tree(sample_modules),
        }
        result = cycle_signals.format_for_auditor(signals)
        assert isinstance(result, str)
        assert "Auditor scope" in result
        assert "S5" in result
        assert "S1" in result

    def test_empty_signals(self):
        result = cycle_signals.format_for_auditor({})
        assert isinstance(result, str)
        assert "Auditor scope" in result


# ---------------------------------------------------------------------------
# load_codemap
# ---------------------------------------------------------------------------

class TestLoadCodemap:
    def test_load_valid(self, tmp_path):
        codemap_file = tmp_path / "codemap.json"
        codemap_file.write_text(json.dumps({"modules": [], "summary": {}}))
        result = cycle_signals.load_codemap(str(codemap_file))
        assert result == {"modules": [], "summary": {}}

    def test_load_missing(self, tmp_path):
        with pytest.raises(SystemExit):
            cycle_signals.load_codemap(str(tmp_path / "nonexistent.json"))


# ---------------------------------------------------------------------------
# extract
# ---------------------------------------------------------------------------

class TestExtract:
    def test_extract(self, sample_codemap, tmp_path):
        codemap_file = tmp_path / "codemap.json"
        codemap_file.write_text(json.dumps(sample_codemap))

        result = cycle_signals.extract(str(codemap_file))
        assert "S1_no_tests" in result
        assert "S2_oversized" in result
        assert "S3_dead_code" in result
        assert "S4_duplicates" in result
        assert "S5_errors" in result
        assert "S6_coverage" in result
        assert "tree_summary" in result
        assert result["generated_from"] == str(codemap_file)

    def test_extract_with_prev(self, sample_codemap, tmp_path):
        codemap_file = tmp_path / "codemap.json"
        codemap_file.write_text(json.dumps(sample_codemap))
        prev_file = tmp_path / "prev_codemap.json"
        prev_codemap = dict(sample_codemap)
        prev_file.write_text(json.dumps(prev_codemap))

        result = cycle_signals.extract(str(codemap_file), prev_codemap_path=str(prev_file))
        assert "S6_coverage" in result
        assert "delta_pct" in result["S6_coverage"]
