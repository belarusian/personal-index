# TICKET-231: Refactor `dedup` in cli_dedup.py (74L → ≤50L)

## What's Wrong

`personal_index/cli_dedup.py:dedup` (line 19, 74 lines) exceeds the 50-line function limit. It bundles content loading, dedup method dispatch, result display, and index mutation into one function.

## Evidence

Reading lines 19–92 of `personal_index/cli_dedup.py`:

1. **Index loading** (lines 39–46): Opens `SearchIndex`, lists pages, handles empty case.
2. **Item building** (lines 49–55): Transforms `Page` objects into dicts for `ContentDeduplicator`.
3. **Method dispatch** (lines 58–66): `if/elif/elif/else` chain selecting dedup method.
4. **Result display** (lines 68–78): Prints summary and duplicate groups.
5. **Index mutation** (lines 80–90): Removes duplicates from index, saves, reports count.

The display and mutation logic (lines 68–90) is ~25 lines of output formatting and database writes that could be separated.

## Impact

- **Separation of concerns**: CLI output formatting, business logic (dedup dispatch), and data mutation are all mixed.
- **Testability**: Cannot test the dedup dispatch logic without also triggering CLI output and index writes.
- **Dry-run coupling**: The `dry_run` flag gates the mutation block but the display logic is always executed, making the control flow harder to follow.

## Suggestion

Extract three sub-functions:
