#!/usr/bin/env python3
"""
Publish dashboard + codemap to belarusian/search GitHub Pages repo.

Usage:
    # Quick: copy existing generated files (no regenerate)
    python -m personal_index.publish_dashboard --search-repo ~/Research/search

    # Full: regenerate from scratch then publish (runs ruff+mypy+pytest, slow)
    python -m personal_index.publish_dashboard --regenerate --search-repo ~/Research/search

    # Dry run: show what would happen without pushing
    python -m personal_index.publish_dashboard --dry-run
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command, printing it for visibility."""
    print(f"[publish] $ {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, check=False)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if check and result.returncode != 0:
        print(f"[publish] ERROR: command failed with exit {result.returncode}", file=sys.stderr)
        sys.exit(1)
    return result


def regenerate(project_root: Path) -> tuple[Path, Path]:
    """Run docs_generator to produce fresh HTML + JSON."""
    print("[publish] Regenerating dashboard (runs ruff+mypy+pytest — this may take a while)...")
    run(["python", "-m", "personal_index.docs_generator"], cwd=project_root)

    html = project_root / "personal_index" / "docs_dashboard.html"
    json_path = project_root / "personal_index" / "docs_dashboard_metadata.json"

    if not html.exists():
        print(f"[publish] ERROR: dashboard HTML not found at {html}", file=sys.stderr)
        sys.exit(1)
    if not json_path.exists():
        print(f"[publish] ERROR: codemap JSON not found at {json_path}", file=sys.stderr)
        sys.exit(1)

    return html, json_path


def validate_sync(html_path: Path, json_path: Path) -> dict:
    """Validate that HTML embedded metadata and JSON codemap are in sync."""
    print("[publish] Validating HTML ↔ JSON sync...")

    # Read JSON codemap
    codemap = json.loads(json_path.read_text(encoding="utf-8"))
    json_summary = codemap.get("summary", {})

    # Extract embedded metadata from HTML
    html_text = html_path.read_text(encoding="utf-8")
    start = html_text.find('<script type="application/json" id="codemap-metadata">')
    end = html_text.find("</script>", start)
    if start == -1 or end == -1:
        print("[publish] WARNING: no embedded codemap metadata found in HTML", file=sys.stderr)
        return {"sync": False, "reason": "no embedded metadata"}

    import html as htmlmod
    embedded_raw = html_text[start + len('<script type="application/json" id="codemap-metadata">'):end]
    embedded = json.loads(htmlmod.unescape(embedded_raw))
    embedded_summary = embedded.get("summary", {})

    # Compare summaries
    mismatches = []
    for key in json_summary:
        if json_summary[key] != embedded_summary.get(key):
            mismatches.append(f"  {key}: JSON={json_summary[key]} vs HTML={embedded_summary.get(key)}")

    if mismatches:
        print("[publish] ERROR: HTML and JSON are out of sync:")
        for m in mismatches:
            print(m)
        return {"sync": False, "mismatches": mismatches}

    print(f"[publish] OK — synced. {json_summary['total_modules']} modules, "
          f"{json_summary['total_errors']} errors, {json_summary['total_warnings']} warnings")
    return {"sync": True, "summary": json_summary}


def _copy_dashboard_files(html_path: Path, json_path: Path, search_repo: Path, dry_run: bool) -> None:
    """Copy HTML and JSON dashboard files to the search repo.

    Args:
        html_path: Source HTML dashboard file.
        json_path: Source JSON codemap file.
        search_repo: Target search repository directory.
        dry_run: If True, only print what would be done.
    """
    dest_html = search_repo / "index.html"
    dest_json = search_repo / "codemap.json"

    print(f"[publish] Copying dashboard → {dest_html}")
    print(f"[publish] Copying codemap   → {dest_json}")

    if not dry_run:
        shutil.copy2(html_path, dest_html)
        shutil.copy2(json_path, dest_json)

    # Run signal extractor against fresh codemap for audit signals
    signals_path = search_repo / "signals.json"
    print(f"[publish] Generating cycle signals → {signals_path}")
    if not dry_run:
        try:
            result = run(
                ["python", "-m", "personal_index.cycle_signals", str(json_path), "--format", "json"],
                cwd=Path.home() / "Research" / "personal-index",
                check=False,
            )
            if result.returncode == 0:
                signals_path.write_text(result.stdout, encoding="utf-8")
        except (OSError, RuntimeError) as e:
            print(f"[publish] WARNING: signal extraction failed: {e}", file=sys.stderr)


def _git_commit_push(json_path: Path, search_repo: Path) -> None:
    """Stage, commit, and push dashboard changes in the search repo.

    Args:
        json_path: Source JSON codemap file (used for commit message).
        search_repo: Target search repository directory.
    """
    run(["git", "add", "index.html", "codemap.json", "signals.json"], cwd=search_repo)

    # Check if there are changes
    status = run(["git", "diff", "--cached", "--quiet"], cwd=search_repo, check=False)
    if status.returncode == 0:
        print("[publish] No changes to commit — files already up to date")
        return

    result = run(["git", "status", "--porcelain"], cwd=search_repo, check=False)
    changed_files = result.stdout.strip()

    summary = json.loads(json_path.read_text(encoding="utf-8")).get("summary", {})
    msg = (f"dashboard: refresh — {summary.get('total_modules', '?')} modules, "
           f"{summary.get('total_lines', '?')} lines, "
           f"{summary.get('total_errors', '?')} errors, "
           f"{summary.get('total_warnings', '?')} warnings\n\n"
           f"Files changed:\n{changed_files}")

    run(["git", "commit", "-m", msg], cwd=search_repo)
    run(["git", "push", "origin", "HEAD"], cwd=search_repo)


def publish(html_path: Path, json_path: Path, search_repo: Path, dry_run: bool = False) -> None:
    """Copy dashboard files to search repo and optionally push."""
    if not search_repo.is_dir():
        print(f"[publish] ERROR: search repo not found at {search_repo}", file=sys.stderr)
        sys.exit(1)

    _copy_dashboard_files(html_path, json_path, search_repo, dry_run)

    if dry_run:
        print("[publish] DRY RUN — skipping git operations")
        return

    _git_commit_push(json_path, search_repo)

    print("[publish] Done. Dashboard live at: https://belarusian.github.io/search/")


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish dashboard to belarusian/search")
    parser.add_argument(
        "--search-repo",
        default=str(Path.home() / "Research" / "search"),
        help="Path to belarusian/search checkout (default: ~/Research/search)",
    )
    parser.add_argument(
        "--project-root",
        default=str(Path.cwd()),
        help="Path to personal-index project root (default: current dir)",
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Run docs_generator first (slow — runs ruff+mypy+pytest)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making changes",
    )
    args = parser.parse_args()

    project_root = Path(args.project_root)
    search_repo = Path(args.search_repo)

    # Get HTML + JSON paths
    if args.regenerate:
        html, json_path = regenerate(project_root)
    else:
        html = project_root / "personal_index" / "docs_dashboard.html"
        json_path = project_root / "personal_index" / "docs_dashboard_metadata.json"
        if not html.exists():
            print(f"[publish] ERROR: no existing dashboard at {html}", file=sys.stderr)
            print("[publish] Use --regenerate to create one (slow) or generate manually first.", file=sys.stderr)
            sys.exit(1)
        if not json_path.exists():
            print(f"[publish] ERROR: no existing codemap at {json_path}", file=sys.stderr)
            sys.exit(1)

    # Validate sync before publishing
    sync = validate_sync(html, json_path)
    if not sync.get("sync"):
        print("[publish] WARNING: HTML and JSON are out of sync!", file=sys.stderr)
        print("[publish] Consider --regenerate to produce fresh synced files.", file=sys.stderr)
        if not args.dry_run:
            ans = input("[publish] Publish anyway? [y/N] ")
            if ans.lower() != "y":
                print("[publish] Aborted.")
                sys.exit(0)

    publish(html, json_path, search_repo, args.dry_run)


if __name__ == "__main__":
    main()
