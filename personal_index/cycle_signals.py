#!/usr/bin/env python3
"""
Cycle signal extractor.

Reads codemap.json and emits heuristic signals for the next audit cycle.
Output is structured JSON that can be fed directly to the auditor as scope.

Signals:
  S1: modules_with_no_tests    — live modules lacking test coverage
  S2: oversized_modules         — modules >200 lines, candidates for split
  S3: dead_code_candidates      — modules with 0 incoming imports
  S4: potential_duplicates      — modules with overlapping name prefixes
  S5: error_hotspots            — modules with lint/type errors
  S6: coverage_trend            — test coverage delta from previous cycle
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Tree summary — hierarchical grouping for LLM-friendly consumption
# ---------------------------------------------------------------------------

def _update_node_stats(node: dict, module: dict, is_leaf: bool, part: str) -> None:
    """Update stats on a tree node for one module.

    Args:
        node: Tree node dict to update in-place.
        module: Module dict from codemap with stats fields.
        is_leaf: Whether this node represents the module itself (leaf).
        part: The leaf module name segment (used for signal detection).
    """
    if is_leaf:
        node["modules"].append(node["full_path"])
        node["stats"]["modules"] += 1
        node["stats"]["lines"] += module.get("lines", 0)
        node["stats"]["functions"] += module.get("functions", 0)
        node["stats"]["classes"] += module.get("classes", 0)
        node["stats"]["errors"] += module.get("ruff_errors", 0) + module.get("mypy_errors", 0)
        node["stats"]["warnings"] += module.get("ruff_warnings", 0)

        # Detect signals on leaf modules
        signals = _detect_module_signals(module, part)
        node["signals"].update(signals)
    else:
        # Accumulate stats up the tree
        node["stats"]["lines"] += module.get("lines", 0)
        node["stats"]["functions"] += module.get("functions", 0)
        node["stats"]["classes"] += module.get("classes", 0)
        node["stats"]["errors"] += module.get("ruff_errors", 0) + module.get("mypy_errors", 0)
        node["stats"]["warnings"] += module.get("ruff_warnings", 0)
        node["stats"]["modules"] += 1


def _walk_module_path(tree: dict[str, dict], parts: list[str], module: dict) -> None:
    """Walk the dotted path of a module name, creating and updating tree nodes.

    Args:
        tree: Flat tree dict, updated in-place.
        parts: Dotted name split into segments (e.g., ["pkg", "sub", "mod"]).
        module: Module dict from codemap with stats fields.
    """
    current_path: list[str] = []
    for i, part in enumerate(parts):
        current_path.append(part)
        key = ".".join(current_path)

        if key not in tree:
            tree[key] = {
                "name": part,
                "full_path": key,
                "children": {},
                "modules": [],
                "stats": {
                    "lines": 0,
                    "functions": 0,
                    "classes": 0,
                    "errors": 0,
                    "warnings": 0,
                    "modules": 0,
                },
                "signals": set(),
            }

        node = tree[key]
        is_leaf = i == len(parts) - 1
        _update_node_stats(node, module, is_leaf, part)


def _create_tree_nodes(modules: list[dict]) -> dict[str, dict]:
    """Walk module dotted names and create/update flat tree nodes with stats.

    Args:
        modules: List of module dicts from codemap.

    Returns:
        Flat dict mapping dotted path keys to tree node dicts.
    """
    tree: dict[str, dict] = {}

    for m in modules:
        name = m.get("name", "")
        parts = name.split(".")
        # Skip the root package name (e.g., "personal_index")
        if len(parts) <= 1:
            continue

        _walk_module_path(tree, parts, m)

    # Propagate signals up the tree
    for key, node in tree.items():
        parts = key.split(".")
        for i in range(len(parts) - 1):
            parent_key = ".".join(parts[:i + 1])
            if parent_key in tree:
                tree[parent_key]["signals"].update(node["signals"])

    return tree



def _detect_module_signals(module: dict, short_name: str) -> list[str]:
    """Detect S1/S2/S5 signals on a single module.

    Args:
        module: Module dict from codemap with stats fields.
        short_name: The leaf module name (e.g., "analytics" from "pkg.analytics").

    Returns:
        List of active signal tags (e.g., ["S1", "S2", "S5"]).
    """
    signals: list[str] = []

    # S1 is noisy at 0% coverage — only flag when co-occurring with S2 or S5
    has_s1 = module.get("tests", 0) == 0 and module.get("functions", 0) > 0
    if short_name in ("__init__", "__main__") or short_name.startswith(("cli_", "test_")):
        has_s1 = False
    has_s2 = module.get("lines", 0) >= 200 and module.get("functions", 0) >= 15
    total_err = (
        module.get("ruff_errors", 0)
        + module.get("mypy_errors", 0)
        + module.get("ruff_warnings", 0)
    )
    has_s5 = total_err > 0

    if has_s1 and has_s2:
        signals.append("S1")
    if has_s1 and has_s5:
        signals.append("S1")
    if has_s2:
        signals.append("S2")
    if has_s5:
        signals.append("S5")

    return signals


def _find_top_level(tree: dict[str, dict]) -> set[str]:
    """Find top-level keys (direct children of root)."""
    top_level: set[str] = set()
    for key in tree:
        parts = key.split(".")
        top_level.add(parts[0])
    return top_level


def _aggregate_child_stats(children: dict[str, dict]) -> tuple[dict, list[str]]:
    """Compute root stats from all children."""
    root_stats = {
        "lines": 0,
        "functions": 0,
        "classes": 0,
        "errors": 0,
        "warnings": 0,
        "modules": 0,
    }
    root_signals: set[str] = set()
    for child in children.values():
        for k in root_stats:
            root_stats[k] += child["stats"].get(k, 0)
        root_signals.update(child.get("signals", []))
    return root_stats, sorted(root_signals)


def _tree_to_nested(tree: dict[str, dict]) -> dict:
    """Convert flat tree dict to hierarchical nested structure."""
    top_level = _find_top_level(tree)
    children: dict[str, dict] = {}
    for tl in sorted(top_level):
        if tl in tree:
            children[tl] = _node_to_dict(tl, tree)
    root_stats, root_signals = _aggregate_child_stats(children)
    return {
        "name": "root",
        "stats": root_stats,
        "signals": root_signals,
        "children": children,
    }


def _node_to_dict(key: str, tree: dict[str, dict]) -> dict:
    """Convert a tree node to its final dict representation."""
    node = tree[key]
    name = node["name"]
    children: dict[str, dict] = {}

    # Find direct children
    prefix = key + "."
    for child_key in tree:
        if child_key.startswith(prefix) and child_key != key:
            child_parts = child_key[len(prefix):].split(".")
            if child_parts and child_parts[0]:
                tl = child_parts[0]
                if tl not in children:
                    children[tl] = _node_to_dict(child_key, tree)

    # Only include modules that have signals (keep it compact)
    signal_modules: list[str] = []
    if not children:  # leaf node
        signal_modules.extend(node["modules"])

    # Convert signals set to sorted list
    signals = sorted(node["signals"])

    result: dict = {
        "name": name,
        "stats": node["stats"],
        "signals": signals,
    }

    if children:
        result["children"] = _sort_children(children)

    if signal_modules:
        result["modules"] = signal_modules

    return result


def _sort_children(children: dict[str, dict]) -> dict[str, dict]:
    """Sort children: nodes with errors/signals first, then by module count desc."""
    def sort_key(item: tuple[str, dict]) -> tuple[int, int, int, str]:
        name, node = item
        has_signals = 0 if node.get("signals") else 1
        errors = -(node.get("stats", {}).get("errors", 0))
        modules = -(node.get("stats", {}).get("modules", 0))
        return (has_signals, errors, modules, name)

    return dict(sorted(children.items(), key=sort_key))


def build_tree(modules: list[dict]) -> dict:
    """Group modules into a hierarchical tree by package path.

    Returns a tree node with aggregate stats. Each node has:
      - name: package/module name
      - children: nested package nodes (sorted by error count desc, then name)
      - modules: leaf module names (only modules with signals, to keep it compact)
      - stats: {lines, functions, classes, errors, warnings, modules}
      - signals: list of active signal tags [S1, S2, S5, ...]
    """
    flat_tree = _create_tree_nodes(modules)
    return _tree_to_nested(flat_tree)


def format_tree(tree: dict, max_depth: int = 2, max_lines: int = 50) -> str:
    """Pruned tree summary for LLM consumption.

    Strategy: show top-level packages, collapse clean subtrees into
    a single line, only expand nodes that carry signals.
    Target: ~15-30 lines total, so the LLM sees the shape without noise.

    Args:
        tree: tree from build_tree()
        max_depth: max tree depth to expand (1 = top-level only, 2 = expand flagged packages)
        max_lines: hard cap on output lines
    """
    lines: list[str] = []
    root = tree.get("children", {})
    if not root:
        return "no packages found"

    children = list(root.items())
    flagged = [(n, c) for n, c in children if c.get("signals")]
    clean = [(n, c) for n, c in children if not c.get("signals")]

    for name, node in flagged:
        _render_summary_node(name, node, lines, "", depth=1, max_depth=max_depth)

    if clean and len(lines) < max_lines - 3:
        total_mods = sum(c["stats"]["modules"] for _, c in clean)
        total_lines_count = sum(c["stats"]["lines"] for _, c in clean)
        total_funcs = sum(c["stats"]["functions"] for _, c in clean)
        clean_names = [n for n, _ in clean]
        if len(clean_names) <= 8:
            for name, node in clean:
                _render_summary_node(name, node, lines, "", depth=1, max_depth=max_depth)
        else:
            lines.append(f"  [{len(clean)} clean packages: {', '.join(clean_names[:5])}... — {total_mods}m {total_lines_count:,}L {total_funcs}f]")

    return "\n".join(lines)


def _render_summary_node(name: str, node: dict, lines: list[str], prefix: str, depth: int = 1, max_depth: int = 2) -> None:
    """Render one node line with signal annotations."""
    stats = node.get("stats", {})
    signals = node.get("signals", [])

    stat_str = f"{stats['modules']}m {stats['lines']:,}L {stats['functions']}f"
    signal_str = ""
    if signals:
        signal_str = f" [{','.join(signals)}]"

    lines.append(f"{prefix}{name}: {stat_str}{signal_str}")

    # Only expand children if within depth limit AND this node has signals AND has children
    children = node.get("children", {})
    if children and signals and depth < max_depth:
        child_items = list(children.items())
        child_flagged = [(n, c) for n, c in child_items if c.get("signals")]
        child_clean = [(n, c) for n, c in child_items if not c.get("signals")]

        for cn, cn_node in child_flagged:
            _render_summary_node(cn, cn_node, lines, "  └ ", depth=depth + 1, max_depth=max_depth)

        if child_clean:
            cm = sum(c["stats"]["modules"] for _, c in child_clean)
            cl = sum(c["stats"]["lines"] for _, c in child_clean)
            cf = sum(c["stats"]["functions"] for _, c in child_clean)
            lines.append(f"  └ [{len(child_clean)} clean: {cm}m {cl:,}L {cf}f]")
    elif children and depth >= max_depth:
        # At max depth — collapse remaining children
        total_children = len(children)
        cm = sum(c["stats"]["modules"] for c in children.values())
        cl = sum(c["stats"]["lines"] for c in children.values())
        cf = sum(c["stats"]["functions"] for c in children.values())
        lines.append(f"  └ [{total_children} children collapsed: {cm}m {cl:,}L {cf}f]")


def load_codemap(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        print(f"[signal] ERROR: codemap not found at {p}", file=sys.stderr)
        sys.exit(1)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[signal] ERROR: codemap is not valid JSON at {p}: {exc}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(data, dict):
        print(f"[signal] ERROR: codemap must be a JSON object at {p}", file=sys.stderr)
        sys.exit(1)
    return data


# ---------------------------------------------------------------------------
# S1: modules with no tests (exclude __init__, __main__, cli_*, test_*)
# ---------------------------------------------------------------------------

def signal_no_tests(modules: list[dict]) -> list[dict]:
    """Live modules with 0 tests, excluding scaffolding and CLI entry points."""
    skip_prefixes = ("cli_", "test_")
    skip_names = ("__init__", "__main__")

    results = []
    for m in modules:
        name = m["name"]
        short = name.rpartition(".")[2] if "." in name else name

        if short in skip_names:
            continue
        if any(short.startswith(p) for p in skip_prefixes):
            continue
        if m["tests"] == 0 and m["functions"] > 0:
            results.append({
                "module": name,
                "lines": m["lines"],
                "functions": m["functions"],
                "classes": m["classes"],
                "severity": "high" if m["lines"] > 100 else "medium",
            })

    return sorted(results, key=lambda x: x["lines"], reverse=True)


# ---------------------------------------------------------------------------
# S2: oversized modules (>200 lines, >15 functions)
# ---------------------------------------------------------------------------

def signal_oversized(modules: list[dict], line_threshold: int = 200, func_threshold: int = 15) -> list[dict]:
    results = []
    for m in modules:
        if m["lines"] >= line_threshold and m["functions"] >= func_threshold:
            results.append({
                "module": m["name"],
                "lines": m["lines"],
                "functions": m["functions"],
                "classes": m["classes"],
                "severity": "critical" if m["lines"] > 400 else "high",
            })
    return sorted(results, key=lambda x: x["lines"], reverse=True)


# ---------------------------------------------------------------------------
# S3: dead code — modules nobody imports
# ---------------------------------------------------------------------------

def _collect_imported(modules: list[dict], dep_graph: dict) -> set[str]:
    """Build set of imported module names from dep graph and module imports."""
    all_imported: set[str] = set()
    for deps in dep_graph.values():
        all_imported.update(deps)
    for m in modules:
        for imp in m.get("imports", []):
            mod = imp.rpartition(".")[0]
            all_imported.add(mod)
    return all_imported


def _find_unimported(modules: list[dict], all_imported: set[str]) -> list[dict]:
    """Find unimported modules that have logic."""
    skip_names = ("__init__", "__main__")
    results = []
    for m in modules:
        name = m["name"]
        short = name.rpartition(".")[2] if "." in name else name
        if short in skip_names:
            continue
        has_logic = m["functions"] > 0 or m["classes"] > 0
        is_imported = name in all_imported
        if not is_imported and has_logic:
            results.append({
                "module": name,
                "lines": m["lines"],
                "functions": m["functions"],
                "classes": m["classes"],
                "confidence": "low",
            })
    return sorted(results, key=lambda x: x["lines"])


def signal_dead_code(modules: list[dict], dep_graph: dict) -> list[dict]:
    """Modules with no static incoming imports.

    IMPORTANT: these are candidates only — dynamic dispatch (cli.py, __init__.py
    re-exports, API routing) means many unimported modules are still live.
    Confidence is intentionally low; outer loop must verify before acting.
    """
    all_imported = _collect_imported(modules, dep_graph)
    return _find_unimported(modules, all_imported)


# ---------------------------------------------------------------------------
# S4: potential duplicates — overlapping name stems
# ---------------------------------------------------------------------------

def signal_duplicates(modules: list[dict]) -> list[dict]:
    """Modules sharing the same base stem (e.g., content_export, content_exporter)."""
    stems: dict[str, list[str]] = defaultdict(list)

    for m in modules:
        name = m["name"].rpartition(".")[2]
        stem = name.replace("_", "")[:12]
        stems[stem].append(m["name"])

    results = []
    for stem, names in stems.items():
        if len(names) >= 2:
            unique_stems = {n.rpartition(".")[2] for n in names}
            if len(unique_stems) >= 2:
                results.append({
                    "stem": stem,
                    "modules": sorted(names),
                    "count": len(names),
                })

    return sorted(results, key=lambda x: x["count"], reverse=True)


# ---------------------------------------------------------------------------
# S5: error hotspots
# ---------------------------------------------------------------------------

def signal_errors(modules: list[dict]) -> list[dict]:
    results = []
    for m in modules:
        total = m.get("ruff_errors", 0) + m.get("mypy_errors", 0) + m.get("ruff_warnings", 0)
        if total > 0:
            results.append({
                "module": m["name"],
                "ruff_errors": m.get("ruff_errors", 0),
                "mypy_errors": m.get("mypy_errors", 0),
                "ruff_warnings": m.get("ruff_warnings", 0),
                "total": total,
            })
    return sorted(results, key=lambda x: x["total"], reverse=True)


# ---------------------------------------------------------------------------
# S6: coverage summary
# ---------------------------------------------------------------------------

def signal_coverage(modules: list[dict], test_dir: str | None = None) -> dict:
    """Estimate coverage by matching test files to source module names.

    e.g., tests/test_analytics.py → personal_index.analytics
    Falls back to codemap `tests` field if no test directory found.
    """
    import glob as globmod

    covered_modules: set[str] = set()

    if test_dir and Path(test_dir).is_dir():
        for tf in globmod.glob(f"{test_dir}/test_*.py"):
            tname = Path(tf).stem  # e.g., test_analytics
            stem = tname.replace("test_", "", 1)  # analytics
            # Match against module short names
            for m in modules:
                short = m["name"].rpartition(".")[2]
                if short == stem or f"_{stem}" == short:
                    covered_modules.add(m["name"])

    total = len(modules)
    covered = len(covered_modules)
    return {
        "total_modules": total,
        "modules_with_tests": covered,
        "modules_without_tests": total - covered,
        "coverage_pct": round(covered / total * 100, 1) if total else 0,
        "test_dir_used": test_dir,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def extract(codemap_path: str, prev_codemap_path: str | None = None, test_dir: str | None = None) -> dict:
    codemap = load_codemap(codemap_path)
    modules = codemap.get("modules", [])
    dep_graph = codemap.get("dependency_graph", {})
    summary = codemap.get("summary", {})
    test_dir = _detect_test_dir(codemap_path, test_dir)
    tree = build_tree(modules)
    signals = _build_signals(codemap_path, codemap, summary, tree, modules, dep_graph, test_dir)
    if prev_codemap_path:
        _add_coverage_delta(signals, prev_codemap_path, test_dir)
    return signals


def _detect_test_dir(codemap_path: str, test_dir: str | None) -> str | None:
    """Auto-detect test directory if not given."""
    if test_dir is not None:
        return test_dir
    cm_base = Path(codemap_path).parent
    for candidate in ["tests", "../tests", "../../tests"]:
        p = (cm_base / candidate).resolve()
        if p.is_dir():
            return str(p)
    return None


def _build_signals(codemap_path, codemap, summary, tree, modules, dep_graph, test_dir) -> dict:
    """Build signals dict from codemap data."""
    return {
        "generated_from": codemap_path,
        "codemap_generated_at": codemap.get("generated_at", "unknown"),
        "summary": summary,
        "tree_summary": tree,
        "S1_no_tests": signal_no_tests(modules),
        "S2_oversized": signal_oversized(modules),
        "S3_dead_code": signal_dead_code(modules, dep_graph),
        "S4_duplicates": signal_duplicates(modules),
        "S5_errors": signal_errors(modules),
        "S6_coverage": signal_coverage(modules, test_dir),
    }


def _add_coverage_delta(signals: dict, prev_path: str, test_dir: str | None) -> None:
    """Add coverage delta from previous codemap."""
    try:
        prev = load_codemap(prev_path)
        prev_cov = signal_coverage(prev.get("modules", []), test_dir)
        signals["S6_coverage"]["previous"] = prev_cov
        signals["S6_coverage"]["delta_pct"] = round(
            signals["S6_coverage"]["coverage_pct"] - prev_cov["coverage_pct"], 1
        )
    except SystemExit:
        pass


def _format_tree_section(signals: dict, lines: list[str]) -> None:
    tree = signals.get("tree_summary")
    if tree:
        lines.append("\n## Package Tree (hierarchical overview)")
        lines.append(format_tree(tree, max_depth=2))


def _format_errors_section(errors: list[dict], lines: list[str]) -> None:
    if errors:
        lines.append(f"\n## S5: Error hotspots ({len(errors)} modules)")
        for e in errors[:10]:
            lines.append(f"  - {e['module']}: R:{e['ruff_errors']} M:{e['mypy_errors']} W:{e['ruff_warnings']}")


def _format_no_tests_section(no_tests: list[dict], lines: list[str]) -> None:
    if no_tests:
        lines.append(f"\n## S1: Modules without tests ({len(no_tests)} modules, top 15)")
        for m in no_tests[:15]:
            lines.append(f"  - {m['module']}: {m['lines']}L, {m['functions']} funcs [{m['severity']}]")


def _format_oversized_section(oversized: list[dict], lines: list[str]) -> None:
    if oversized:
        lines.append(f"\n## S2: Oversized modules ({len(oversized)} modules)")
        for m in oversized:
            lines.append(f"  - {m['module']}: {m['lines']}L, {m['functions']} funcs [{m['severity']}]")


def _format_dead_code_section(dead: list[dict], lines: list[str]) -> None:
    if dead:
        lines.append(f"\n## S3: Unimported modules ({len(dead)} candidates, VERIFY BEFORE ACTING)")
        for m in dead[:20]:
            lines.append(f"  - {m['module']}: {m['lines']}L, {m['functions']}f [{m['confidence']}]")


def _format_duplicates_section(dupes: list[dict], lines: list[str]) -> None:
    if dupes:
        lines.append(f"\n## S4: Potential duplicates ({len(dupes)} groups)")
        for d in dupes:
            lines.append(f"  - stem '{d['stem']}': {', '.join(d['modules'])}")


def _format_coverage_section(cov: dict, lines: list[str]) -> None:
    lines.append(f"\n## S6: Coverage: {cov.get('coverage_pct', '?')}% "
                 f"({cov.get('modules_with_tests', 0)}/{cov.get('total_modules', 0)} modules)")


def format_for_auditor(signals: dict) -> str:
    """Format signals as a scoped auditor prompt."""
    lines = ["Auditor scope for next cycle (from signal extractor):"]
    _format_tree_section(signals, lines)
    _format_errors_section(signals.get("S5_errors", []), lines)
    _format_no_tests_section(signals.get("S1_no_tests", []), lines)
    _format_oversized_section(signals.get("S2_oversized", []), lines)
    _format_dead_code_section(signals.get("S3_dead_code", []), lines)
    _format_duplicates_section(signals.get("S4_duplicates", []), lines)
    _format_coverage_section(signals.get("S6_coverage", {}), lines)
    return "\n".join(lines)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Extract audit signals from codemap")
    parser.add_argument("codemap", help="Path to codemap.json")
    parser.add_argument("--prev", help="Previous codemap for delta comparison")
    parser.add_argument("--test-dir", help="Path to tests/ directory for coverage estimation")
    parser.add_argument("--format", choices=["json", "auditor", "tree"], default="json",
                        help="Output format")
    parser.add_argument("--depth", type=int, default=2, help="Max tree depth to expand (default: 2)")
    parser.add_argument("--lines", type=int, default=50, help="Max output lines for tree (default: 50)")
    args = parser.parse_args()

    signals = extract(args.codemap, args.prev, args.test_dir)

    if args.format == "json":
        # Convert sets to lists for JSON serialization
        def _serialize(obj):
            if isinstance(obj, set):
                return sorted(obj)
            if isinstance(obj, dict):
                return {k: _serialize(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_serialize(i) for i in obj]
            return obj
        print(json.dumps(_serialize(signals), indent=2))
    elif args.format == "tree":
        tree = signals.get("tree_summary", {})
        print(format_tree(tree, max_depth=args.depth, max_lines=args.lines))
    else:
        print(format_for_auditor(signals))


if __name__ == "__main__":
    main()
