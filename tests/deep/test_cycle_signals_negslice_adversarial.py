"""Adversarial deep tests for cycle_signals.format_tree negative max_lines (cycle 349).

DEFECT (QA-72): ``format_tree`` documents ``max_lines`` as a "hard cap on
output lines" (docstring line 283; docs/cycle-signals.md line 64 "hard-caps
output at ``max_lines``"), and the CLI exposes it as ``--lines`` (type=int,
no lower bound). But the terminal slice ``lines[:max_lines]`` (line 308) has
NO floor guard: a NEGATIVE ``max_lines`` is out-of-range and Python's negative
slice semantics return ALL-BUT-LAST ``abs(max_lines)`` lines instead of an
empty output. ``max_lines=0`` correctly returns "" (empty), so the cap has a
floor at 0 but not below it — the same cap-without-floor class as QA-71
(ProgressTracker.progress_percent). Every sibling top-N/truncate site in the
codebase clamps to 0 first (content_digest.generate max(0,...), formatter
max(0,...), index.search / search_index.search / content_scoring.rank_items
/ content_search.get_suggestions / progress.list_completed / content_recommender
/ keyword_extractor / search_suggestions / tfidf / content_categorizer.top_n
/ content_digest / content_export_csv all guard ``<= 0``); format_tree is the
one unguarded public site.

The negative pin is xfail(strict=True): it documents the defect without
breaking the suite, and XPASSes (turns red) the moment the implementer adds
the floor guard, prompting removal of the marker.
"""


from personal_index.cycle_signals import format_tree


def _flagged_tree(n):
    """Build a tree dict with n flagged top-level packages (each renders a line)."""
    return {
        "name": "root",
        "signals": [],
        "stats": {"modules": n, "lines": n * 10, "functions": n},
        "children": {
            f"pkg{i:02d}": {
                "name": f"pkg{i:02d}",
                "signals": ["S1_no_tests"],
                "stats": {"modules": 1, "lines": 10, "functions": 1},
                "children": {},
            }
            for i in range(n)
        },
    }


def test_format_tree_positive_max_lines_is_a_hard_cap():
    """Regression armor: a positive max_lines truncates to at most that many lines."""
    tree = _flagged_tree(10)
    out = format_tree(tree, max_depth=1, max_lines=3)
    assert len(out.splitlines()) <= 3


def test_format_tree_zero_max_lines_is_empty():
    """Regression armor: max_lines=0 returns empty output (the floor that DOES exist)."""
    tree = _flagged_tree(10)
    out = format_tree(tree, max_depth=1, max_lines=0)
    assert out == ""


def test_format_tree_negative_max_lines_clamps_to_empty():
    """DEFECT pin (QA-72): negative max_lines must clamp to empty, not leak all-but-last."""
    tree = _flagged_tree(10)
    full = format_tree(tree, max_depth=1, max_lines=999)
    full_lines = len(full.splitlines())
    assert full_lines >= 2  # sanity: the tree really renders multiple lines

    out_neg = format_tree(tree, max_depth=1, max_lines=-1)
    # Expected-per-docs (hard cap, negative out-of-range -> empty, like max_lines=0):
    assert out_neg == "", (
        f"negative max_lines leaked {len(out_neg.splitlines())} lines "
        f"(all-but-last of {full_lines}); expected empty output"
    )


def test_format_tree_negative_max_lines_does_not_exceed_full():
    """Property: no max_lines value may return MORE lines than an unbounded render.

    The negative slice returns full_lines-1 lines, which is <= full, so this
    property holds even with the defect — it is included to pin the boundary
    that the leak sits just under, distinguishing it from an unbounded output.
    """
    tree = _flagged_tree(10)
    full_lines = len(format_tree(tree, max_depth=1, max_lines=999).splitlines())
    out_neg = format_tree(tree, max_depth=1, max_lines=-1)
    assert len(out_neg.splitlines()) <= full_lines


def test_format_tree_double_negative_max_lines_clamps_to_empty():
    """Post-fix contract (QA-72): a negative max_lines clamps to 0 -> empty.

    Reconciled from the pre-fix leak-signature pin (IMPL-17 pushback, cycle
    357). The fix floors max_lines at 0, so lines[:max(0, max_lines)] is empty
    for any negative N. Pins the -1 and -2 boundaries (the -1 case is also
    pinned by test_format_tree_negative_max_lines_clamps_to_empty).
    """
    tree = _flagged_tree(10)
    assert format_tree(tree, max_depth=1, max_lines=-1) == ""
    assert format_tree(tree, max_depth=1, max_lines=-2) == ""


# ---------------------------------------------------------------------------
# End-to-end CLI: the defect is user-reachable via `--lines` (type=int, no
# lower bound). `--lines -1` must not exceed the `--lines 0` floor.
# ---------------------------------------------------------------------------

def _write_codemap(tmp_path):
    import json
    mods = [
        {
            "name": f"pkg{i:02d}.mod",
            "lines": 250,
            "functions": 20,
            "classes": 0,
            "tests": 0,
            "ruff_errors": 1,
            "mypy_errors": 0,
            "ruff_warnings": 0,
        }
        for i in range(10)
    ]
    cm = tmp_path / "cm.json"
    cm.write_text(json.dumps({"generated_at": "now", "modules": mods,
                              "dependency_graph": {}, "summary": {}}))
    return str(cm)


def _cli_tree(cm_path, lines):
    import subprocess
    import sys
    r = subprocess.run(
        [sys.executable, "-m", "personal_index.cycle_signals", cm_path,
         "--format", "tree", "--depth", "1", "--lines", str(lines)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_cli_negative_lines_clamps_to_zero_floor(tmp_path):
    """DEFECT pin (QA-72): `--lines -1` must not exceed the `--lines 0` output."""
    cm = _write_codemap(tmp_path)
    zero_out = _cli_tree(cm, 0)
    neg_out = _cli_tree(cm, -1)
    assert len(neg_out.splitlines()) <= len(zero_out.splitlines()) + 1, (
        f"--lines -1 leaked {len(neg_out.splitlines())} lines vs --lines 0 "
        f"{len(zero_out.splitlines())}"
    )
