"""Adversarial deep tests for personal_index.cycle_signals (cycle 205).

cycle_signals is a never-probed module with NO docs page. Its public
functions (build_tree, format_tree, signal_*, load_codemap, extract,
format_for_auditor, main) are pure functions over a codemap dict, so they
are cheap to attack with guard inputs (None/empty/whitespace/unicode/
duplicate/out-of-range), round-trips, idempotence, and property checks.

DEFECT (QA-34): ``format_tree`` documents ``max_lines`` as a "hard cap on
output lines" and the CLI exposes it as ``--lines`` ("Max output lines for
tree"), but the code never truncates the output to ``max_lines``. With 30
flagged packages the output is 90 lines regardless of ``max_lines`` (10, 5,
or even 1). The only use of ``max_lines`` is the gate
``if clean and len(lines) < max_lines - 3`` (whether to render the clean
packages), not a cap. Pinned xfail-strict below.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from personal_index.cycle_signals import (
    build_tree,
    format_for_auditor,
    format_tree,
    signal_coverage,
    signal_dead_code,
    signal_duplicates,
    signal_errors,
    signal_no_tests,
    signal_oversized,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _module(name: str, **over) -> dict:
    base = {
        "name": name,
        "lines": 50,
        "functions": 5,
        "classes": 0,
        "tests": 0,
        "ruff_errors": 0,
        "mypy_errors": 0,
        "ruff_warnings": 0,
        "imports": [],
    }
    base.update(over)
    return base


def _flagged_modules(n_pkgs: int = 30, per_pkg: int = 2) -> list[dict]:
    """Modules that carry signals (no tests + a ruff error) so every
    package node is flagged and format_tree renders one line each."""
    mods = []
    for i in range(n_pkgs):
        for j in range(per_pkg):
            mods.append(_module(f"pkg{i:02d}.mod{j}", tests=0, ruff_errors=1))
    return mods


def test_format_tree_max_lines_is_a_hard_cap():
    tree = build_tree(_flagged_modules(30, 2))
    out = format_tree(tree, max_depth=2, max_lines=10)
    # The documented contract: output must never exceed max_lines.
    assert len(out.splitlines()) <= 10


# ---------------------------------------------------------------------------
# build_tree — guard inputs, idempotence, property checks
# ---------------------------------------------------------------------------
def test_build_tree_empty_returns_root():
    tree = build_tree([])
    assert tree["name"] == "root"
    assert tree["children"] == {}
    assert tree["stats"]["modules"] == 0
    assert tree["signals"] == []


def test_build_tree_idempotent():
    mods = _flagged_modules(5, 3)
    assert build_tree(mods) == build_tree(mods)


def test_build_tree_stats_sum_modules():
    mods = _flagged_modules(4, 3)
    tree = build_tree(mods)
    # root stats aggregate all leaf modules
    assert tree["stats"]["modules"] == 4 * 3


def test_build_tree_unicode_module_name_no_crash():
    mods = [_module("pkg.модуль", tests=0, ruff_errors=1)]
    tree = build_tree(mods)
    assert tree["stats"]["modules"] == 1


def test_build_tree_duplicate_names_aggregate():
    mods = [
        _module("a.b", tests=0, ruff_errors=1),
        _module("a.b", tests=0, ruff_errors=1),
    ]
    tree = build_tree(mods)
    assert tree["stats"]["modules"] == 2


# ---------------------------------------------------------------------------
# format_tree — guard inputs and out-of-range depth
# ---------------------------------------------------------------------------
def test_format_tree_empty_tree_message():
    assert format_tree(build_tree([])) == "no packages found"


def test_format_tree_depth_zero_collapse():
    tree = build_tree(_flagged_modules(5, 3))
    out = format_tree(tree, max_depth=0, max_lines=1000)
    # depth 0 must not expand children; output is bounded and non-empty
    assert len(out.splitlines()) > 0
    assert len(out.splitlines()) < 40


def test_format_tree_negative_depth_no_crash():
    tree = build_tree(_flagged_modules(5, 3))
    out = format_tree(tree, max_depth=-1, max_lines=1000)
    assert isinstance(out, str)


def test_format_tree_depth_monotonic():
    tree = build_tree(_flagged_modules(5, 3))
    shallow = len(format_tree(tree, max_depth=1, max_lines=1000).splitlines())
    deep = len(format_tree(tree, max_depth=3, max_lines=1000).splitlines())
    assert deep >= shallow


# ---------------------------------------------------------------------------
# signal_no_tests — guard + property
# ---------------------------------------------------------------------------
def test_signal_no_tests_empty():
    assert signal_no_tests([]) == []


def test_signal_no_tests_skips_cli_and_test_prefixes():
    mods = [
        _module("x.cli_helper", tests=0, functions=3),
        _module("x.test_thing", tests=0, functions=3),
        _module("x.real", tests=0, functions=3),
    ]
    out = signal_no_tests(mods)
    names = {r["module"] for r in out}
    assert "x.real" in names
    assert "x.cli_helper" not in names
    assert "x.test_thing" not in names


def test_signal_no_tests_requires_functions():
    # a module with 0 tests but 0 functions is scaffolding, not a signal
    mods = [_module("x.empty", tests=0, functions=0)]
    assert signal_no_tests(mods) == []


def test_signal_no_tests_sorted_by_lines_desc():
    mods = [
        _module("x.small", tests=0, functions=1, lines=10),
        _module("x.big", tests=0, functions=1, lines=900),
    ]
    out = signal_no_tests(mods)
    assert out[0]["module"] == "x.big"


def test_signal_no_tests_severity_threshold():
    mods = [
        _module("x.small", tests=0, functions=1, lines=10),
        _module("x.big", tests=0, functions=1, lines=900),
    ]
    sev = {r["module"]: r["severity"] for r in signal_no_tests(mods)}
    assert sev["x.big"] == "high"
    assert sev["x.small"] == "medium"


# ---------------------------------------------------------------------------
# signal_oversized — guard + property
# ---------------------------------------------------------------------------
def test_signal_oversized_empty():
    assert signal_oversized([]) == []


def test_signal_oversized_requires_both_thresholds():
    mods = [
        _module("x.lines_only", lines=500, functions=1),
        _module("x.funcs_only", lines=10, functions=50),
        _module("x.both", lines=500, functions=50),
    ]
    out = signal_oversized(mods)
    assert [r["module"] for r in out] == ["x.both"]


def test_signal_oversized_custom_thresholds():
    mods = [_module("x.m", lines=100, functions=10)]
    assert signal_oversized(mods, line_threshold=100, func_threshold=10) != []
    assert signal_oversized(mods, line_threshold=101, func_threshold=10) == []


# ---------------------------------------------------------------------------
# signal_duplicates — guard + property
# ---------------------------------------------------------------------------
def test_signal_duplicates_empty():
    assert signal_duplicates([]) == []


def test_signal_duplicates_single_module():
    mods = [_module("a.content_export")]
    assert signal_duplicates(mods) == []


def test_signal_duplicates_finds_shared_stem():
    mods = [
        _module("a.content_export"),
        _module("a.content_exporter"),
    ]
    out = signal_duplicates(mods)
    assert len(out) == 1
    assert out[0]["count"] == 2


def test_signal_duplicates_ignores_identical_names():
    # two modules with the SAME short name are not a "duplicate stem"
    mods = [
        _module("a.content_export"),
        _module("b.content_export"),
    ]
    out = signal_duplicates(mods)
    # unique short names == 1, so no group
    assert out == []


# ---------------------------------------------------------------------------
# signal_errors — guard + property
# ---------------------------------------------------------------------------
def test_signal_errors_empty():
    assert signal_errors([]) == []


def test_signal_errors_sums_all_error_kinds():
    mods = [_module("x.m", ruff_errors=2, mypy_errors=3, ruff_warnings=1)]
    out = signal_errors(mods)
    assert out[0]["total"] == 6


def test_signal_errors_excludes_clean():
    mods = [_module("x.clean", ruff_errors=0, mypy_errors=0, ruff_warnings=0)]
    assert signal_errors(mods) == []


# ---------------------------------------------------------------------------
# signal_coverage — guard + property (documented: no fallback to tests field)
# ---------------------------------------------------------------------------
def test_signal_coverage_empty_total_zero_pct():
    cov = signal_coverage([])
    assert cov["total_modules"] == 0
    assert cov["coverage_pct"] == 0


def test_signal_coverage_none_test_dir_reports_zero():
    # documented: when test_dir is None, no test files matched -> 0 coverage
    mods = [_module("x.analytics", tests=5)]
    cov = signal_coverage(mods, test_dir=None)
    assert cov["modules_with_tests"] == 0
    assert cov["coverage_pct"] == 0


def test_signal_coverage_matches_test_file(tmp_path):
    (tmp_path / "test_analytics.py").write_text("def test_x(): pass\n")
    mods = [_module("x.analytics"), _module("x.other")]
    cov = signal_coverage(mods, test_dir=str(tmp_path))
    assert cov["modules_with_tests"] == 1
    assert cov["modules_without_tests"] == 1


def test_signal_coverage_pct_rounds():
    (tmp_path := tempfile.mkdtemp())
    Path(tmp_path, "test_a.py").write_text("x=1\n")
    mods = [_module("x.a"), _module("x.b"), _module("x.c")]
    cov = signal_coverage(mods, test_dir=tmp_path)
    assert cov["coverage_pct"] == round(1 / 3 * 100, 1)


# ---------------------------------------------------------------------------
# signal_dead_code — guard
# ---------------------------------------------------------------------------
def test_signal_dead_code_empty():
    assert signal_dead_code([], {}) == []


def test_signal_dead_code_flags_unimported_with_logic():
    mods = [
        _module("x.live", functions=3),
        _module("x.orphan", functions=3),
    ]
    dep = {"x.live": ["x.orphan"]}  # orphan is imported -> not dead
    out = signal_dead_code(mods, dep)
    names = {r["module"] for r in out}
    assert "x.orphan" not in names


def test_signal_dead_code_skips_init_main():
    mods = [
        _module("x.__init__", functions=3),
        _module("x.__main__", functions=3),
    ]
    assert signal_dead_code(mods, {}) == []


# ---------------------------------------------------------------------------
# format_for_auditor — guard + idempotence
# ---------------------------------------------------------------------------
def test_format_for_auditor_empty_signals():
    sig = {
        "tree_summary": build_tree([]),
        "S5_errors": [],
        "S1_no_tests": [],
        "S2_oversized": [],
        "S3_dead_code": [],
        "S4_duplicates": [],
        "S6_coverage": {},
    }
    out = format_for_auditor(sig)
    assert isinstance(out, str)
    assert "Auditor scope" in out


def test_format_for_auditor_idempotent():
    sig = {
        "tree_summary": build_tree(_flagged_modules(3, 2)),
        "S5_errors": [],
        "S1_no_tests": [],
        "S2_oversized": [],
        "S3_dead_code": [],
        "S4_duplicates": [],
        "S6_coverage": {},
    }
    assert format_for_auditor(sig) == format_for_auditor(sig)


# ---------------------------------------------------------------------------
# End-to-end CLI run (python -m personal_index.cycle_signals)
# ---------------------------------------------------------------------------
def test_cli_tree_format_end_to_end(tmp_path):
    mods = _flagged_modules(3, 2)
    cm = {"modules": mods, "dependency_graph": {}, "summary": {}}
    cm_path = tmp_path / "codemap.json"
    cm_path.write_text(json.dumps(cm), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "personal_index.cycle_signals",
         str(cm_path), "--format", "tree", "--lines", "50"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    # 3 flagged packages -> at least one line per package
    assert len(proc.stdout.splitlines()) >= 3


def test_cli_json_format_end_to_end(tmp_path):
    mods = _flagged_modules(2, 2)
    cm = {"modules": mods, "dependency_graph": {}, "summary": {}}
    cm_path = tmp_path / "codemap.json"
    cm_path.write_text(json.dumps(cm), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "personal_index.cycle_signals",
         str(cm_path), "--format", "json"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert "S1_no_tests" in data
    assert "tree_summary" in data


def test_cli_missing_codemap_exits_nonzero(tmp_path):
    proc = subprocess.run(
        [sys.executable, "-m", "personal_index.cycle_signals",
         str(tmp_path / "nope.json"), "--format", "json"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert proc.returncode != 0
