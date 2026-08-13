# TICKET-11-2: Extract helpers from `cli_verify.verify` (66L → ~35L)

## File
`personal_index/cli_verify.py`, lines 238–305

## Evidence

The `verify` CLI command (lines 238–305) performs three distinct logical phases:

1. **Check runner loop** (lines 258–296): Defines a local `check()` closure, then calls 6 individual check functions + the full pipeline check, accumulating results.
2. **Cleanup of verify artifacts** (lines 299–302): Removes `verify_interests.json`, `verify_tags.json`, `verify_index.json` from the data dir.
3. **Summary display** (line 305): Delegates to `_build_summary()` — already extracted.

The local `check()` closure (lines 258–266) captures `checks_passed` and `checks_total` via `nonlocal`, making the accumulation logic hard to test in isolation. The 6 individual checks + pipeline check are a repetitive pattern that could be data-driven.

## Impact

- The local `check()` closure cannot be unit-tested independently.
- Adding a new check requires modifying the function body (not closed for extension).
- Cleanup logic is mixed with the check orchestration.

## Suggestion

Extract two private helpers:

### Helper 1: `_run_individual_checks`
