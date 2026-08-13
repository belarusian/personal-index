# TICKET-11-3: Extract helpers from `publish_dashboard.publish` (59L → ~25L)

## File
`personal_index/publish_dashboard.py`, lines 96–154

## Evidence

The `publish` function performs four distinct logical phases:

1. **Validation** (lines 98–100): Checks that `search_repo` is a directory.
2. **File copy** (lines 102–111): Copies HTML and JSON to the search repo (skipped in dry-run).
3. **Signal generation** (lines 113–126): Runs `cycle_signals` module to produce `signals.json` (skipped in dry-run).
4. **Git commit + push** (lines 128–154): Stages files, checks for changes, builds commit message from codemap summary, commits, pushes.

The git operations block (lines 128–154) is the largest sub-task at ~27 lines and contains its own sub-logic: diff check, status check, message construction, commit, push.

## Impact

- The function mixes file I/O, subprocess invocation, and git operations — three different concerns.
- The git commit/push logic cannot be unit-tested without mocking the entire function.
- Dry-run logic is scattered across three separate `if not dry_run` / `if dry_run` branches.

## Suggestion

Extract two private helpers:

### Helper 1: `_copy_dashboard_files`
