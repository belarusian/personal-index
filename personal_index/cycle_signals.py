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


def load_codemap(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        print(f"[signal] ERROR: codemap not found at {p}", file=sys.stderr)
        sys.exit(1)
    return json.loads(p.read_text(encoding="utf-8"))


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

def signal_dead_code(modules: list[dict], dep_graph: dict) -> list[dict]:
    """Modules with no static incoming imports.

    IMPORTANT: these are candidates only — dynamic dispatch (cli.py, __init__.py
    re-exports, API routing) means many unimported modules are still live.
    Confidence is intentionally low; outer loop must verify before acting.
    """
    # Build set of imported module names from dep graph
    all_imported: set[str] = set()
    for deps in dep_graph.values():
        all_imported.update(deps)

    # Also check each module's own imports for cross-references
    for m in modules:
        for imp in m.get("imports", []):
            mod = imp.rpartition(".")[0]
            all_imported.add(mod)

    skip_names = ("__init__", "__main__")

    results = []
    for m in modules:
        name = m["name"]
        short = name.rpartition(".")[2] if "." in name else name

        if short in skip_names:
            continue

        has_logic = m["functions"] > 0 or m["classes"] > 0
        is_imported = name in all_imported

        # Flag unimported modules that have logic — candidate for dead code review
        if not is_imported and has_logic:
            results.append({
                "module": name,
                "lines": m["lines"],
                "functions": m["functions"],
                "classes": m["classes"],
                "confidence": "low",  # always low — requires manual verification
            })

    return sorted(results, key=lambda x: x["lines"])


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
            unique_stems = set(n.rpartition(".")[2] for n in names)
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

    # Auto-detect test dir if not given
    if test_dir is None:
        cm_base = Path(codemap_path).parent
        for candidate in ["tests", "../tests", "../../tests"]:
            p = (cm_base / candidate).resolve()
            if p.is_dir():
                test_dir = str(p)
                break

    signals = {
        "generated_from": codemap_path,
        "codemap_generated_at": codemap.get("generated_at", "unknown"),
        "summary": summary,
        "S1_no_tests": signal_no_tests(modules),
        "S2_oversized": signal_oversized(modules),
        "S3_dead_code": signal_dead_code(modules, dep_graph),
        "S4_duplicates": signal_duplicates(modules),
        "S5_errors": signal_errors(modules),
        "S6_coverage": signal_coverage(modules, test_dir),
    }

    if prev_codemap_path:
        try:
            prev = load_codemap(prev_codemap_path)
            prev_cov = signal_coverage(prev.get("modules", []), test_dir)
            signals["S6_coverage"]["previous"] = prev_cov
            signals["S6_coverage"]["delta_pct"] = round(
                signals["S6_coverage"]["coverage_pct"] - prev_cov["coverage_pct"], 1
            )
        except SystemExit:
            pass

    return signals


def format_for_auditor(signals: dict) -> str:
    """Format signals as a scoped auditor prompt."""
    lines = ["Auditor scope for next cycle (from signal extractor):"]

    errors = signals.get("S5_errors", [])
    if errors:
        lines.append(f"\n## S5: Error hotspots ({len(errors)} modules)")
        for e in errors[:10]:
            lines.append(f"  - {e['module']}: R:{e['ruff_errors']} M:{e['mypy_errors']} W:{e['ruff_warnings']}")

    no_tests = signals.get("S1_no_tests", [])
    if no_tests:
        lines.append(f"\n## S1: Modules without tests ({len(no_tests)} modules, top 15)")
        for m in no_tests[:15]:
            lines.append(f"  - {m['module']}: {m['lines']}L, {m['functions']} funcs [{m['severity']}]")

    oversized = signals.get("S2_oversized", [])
    if oversized:
        lines.append(f"\n## S2: Oversized modules ({len(oversized)} modules)")
        for m in oversized:
            lines.append(f"  - {m['module']}: {m['lines']}L, {m['functions']} funcs [{m['severity']}]")

    dead = signals.get("S3_dead_code", [])
    if dead:
        lines.append(f"\n## S3: Unimported modules ({len(dead)} candidates, VERIFY BEFORE ACTING)")
        for m in dead[:20]:
            lines.append(f"  - {m['module']}: {m['lines']}L, {m['functions']}f [{m['confidence']}]")

    dupes = signals.get("S4_duplicates", [])
    if dupes:
        lines.append(f"\n## S4: Potential duplicates ({len(dupes)} groups)")
        for d in dupes:
            lines.append(f"  - stem '{d['stem']}': {', '.join(d['modules'])}")

    cov = signals.get("S6_coverage", {})
    lines.append(f"\n## S6: Coverage: {cov.get('coverage_pct', '?')}% "
                 f"({cov.get('modules_with_tests', 0)}/{cov.get('total_modules', 0)} modules)")

    return "\n".join(lines)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Extract audit signals from codemap")
    parser.add_argument("codemap", help="Path to codemap.json")
    parser.add_argument("--prev", help="Previous codemap for delta comparison")
    parser.add_argument("--test-dir", help="Path to tests/ directory for coverage estimation")
    parser.add_argument("--format", choices=["json", "auditor"], default="json",
                        help="Output format")
    args = parser.parse_args()

    signals = extract(args.codemap, args.prev, args.test_dir)

    if args.format == "json":
        print(json.dumps(signals, indent=2))
    else:
        print(format_for_auditor(signals))


if __name__ == "__main__":
    main()
