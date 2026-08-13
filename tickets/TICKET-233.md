# TICKET-233: Refactor `export_cmd` in cli_export.py (61L → ≤50L)

## What's Wrong

`personal_index/cli_export.py:export_cmd` (line 25, 61 lines) exceeds the 50-line function limit. It bundles page loading, filtering, format dispatch, and output writing into one function.

## Evidence

Reading lines 25–85 of `personal_index/cli_export.py`:

1. **Index/tag store loading** (lines 37–39): Opens `SearchIndex` and `TagStore`.
2. **Query filtering** (lines 43–46): Searches index and filters pages by matching URLs.
3. **Tag filtering** (lines 49–55): Iterates pages, looks up tags, filters by intersection.
4. **Limit application** (lines 58–59): Slices pages list.
5. **Format dispatch** (lines 65–73): `if/elif/elif/elif/else` chain selecting export formatter.
6. **Output writing** (lines 75–80): Writes to file or stdout.

The filtering logic (query + tag + limit) is ~18 lines that operates on the pages list before any formatting concern.

## Impact

- **Readability**: The function mixes data loading, filtering, formatting, and I/O.
- **Testability**: Cannot test filtering logic without also loading the index and writing output.
- **Extensibility**: Adding a new filter criterion (e.g., date range) requires editing the middle of a 61-line function.

## Suggestion

Extract two sub-functions:
