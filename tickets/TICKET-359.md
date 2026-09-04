# TICKET-359: publish_dashboard._copy_dashboard_files docstring omits signals.json

Status: RESOLVED (merged to main c29f418, gh #556 closed)
Module: personal_index/publish_dashboard.py
Class: (b) doc-drift (docstring under-promises the body's behavior)

## Symptom
`_copy_dashboard_files` docstring (line 103) reads:
    "Copy HTML and JSON dashboard files to the search repo."
but the body does MORE than copy the two dashboard files: after copying
index.html and codemap.json it ALSO generates cycle signals and writes them
to `signals.json` in the search repo (lines 122-132:
`signals_path = search_repo / "signals.json"` ... `signals_path.write_text(...)`).
The docstring's "Copy HTML and JSON dashboard files" is a blanket claim that
omits the third file the function actually produces.

## Evidence
- line 103: `"""Copy HTML and JSON dashboard files to the search repo.`
- line 122: `signals_path = search_repo / "signals.json"`
- line 123: `print(f"[publish] Generating cycle signals → {signals_path}")`
- line 132: `signals_path.write_text(result.stdout, encoding="utf-8")`
- line 144: `_git_commit_push` stages `signals.json` too, confirming it is a
  real output of this publish path.

## Minimal additive fix
Reword the docstring to state the exact set of files the function writes into
the search repo: index.html, codemap.json, AND signals.json (cycle signals,
generated via `personal_index.cycle_signals` when not dry-run). Add ONE
behavior test pinning the corrected claim against the returned/observed state:
after `_copy_dashboard_files(..., dry_run=False)` with a mocked `run`, the
search repo contains index.html, codemap.json AND signals.json.

## Issue: #556
