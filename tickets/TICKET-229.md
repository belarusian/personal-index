# TICKET-229: Refactor `_create_tree_nodes` in cycle_signals.py (75L → ≤50L)

## What's Wrong

`personal_index/cycle_signals.py:_create_tree_nodes` (line 28, 75 lines) exceeds the 50-line function limit. It bundles three distinct concerns into one function.

## Evidence

Reading lines 28–102 of `personal_index/cycle_signals.py`:

1. **Node initialization** (lines 47–62): Creates a default node dict with `stats` and `signals` keys. This is a pure data-structure factory.
2. **Stat accumulation** (lines 66–86): Duplicated logic between `is_leaf` branch (lines 66–74) and `else` branch (lines 79–86). Both branches increment `lines`, `functions`, `classes`, `errors`, `warnings`, and `modules` — the only difference is that the leaf branch also appends to `modules` list and detects signals.
3. **Signal propagation** (lines 88–94): A separate post-processing loop that walks the tree and propagates signals upward.

The duplicated stat-accumulation code (lines 66–74 vs 79–86) is nearly identical — 6 lines repeated.

## Impact

- **Maintainability**: Adding a new stat field requires editing 3 places (init, leaf, non-leaf).
- **Testability**: Signal propagation logic cannot be unit-tested in isolation.
- **Readability**: The function does three things, violating Single Responsibility.

## Suggestion

Extract three sub-functions:
