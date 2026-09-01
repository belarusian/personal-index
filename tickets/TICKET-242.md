# TICKET-242: Extract storage calculation and output formatting from `cli.stats`

## Title
`cli.stats` (L732, 61 lines) mixes data gathering, storage calculation, and two output formats — extract private helpers

## Evidence
`personal_index/cli.py`, lines 732–792. The function performs 5 distinct operations:

| Lines | Operation |
|-------|-----------|
| 740–743 | Resolve `data_dir`, open 3 stores |
| 745–748 | Gather counts from stores |
| 750–757 | **Compute storage size** — `os.walk` over data_dir, summing file sizes |
| 759–768 | **JSON output** — `json.dumps` with 5 fields |
| 770–789 | **Text output** — formatted echo with interest listing and human-readable size |

The storage calculation (L750–757) is a self-contained utility that walks a directory tree. The two output branches (JSON vs text) are independent formatting concerns.

## Impact
- 61-line function bundles data gathering, filesystem I/O, and two output formats
- Storage calculation is not reusable from other commands (e.g., `health`, `dashboard`)
- Adding a third output format (e.g., YAML, CSV) would further bloat the function

## Suggestion
Extract two private helpers:

1. **`_compute_storage_bytes(data_dir: str) -> int`**
   - Move L750–757 into this function
   - Walks `data_dir`, sums `os.path.getsize`, catches `OSError`
   - Signature: `_compute_storage_bytes(data_dir: str) -> int`

2. **`_format_stats_text(page_count: int, interest_count: int, tag_count: int, tagged_count: int, interests: list, storage_bytes: int) -> None`**
   - Move L770–789 into this function
   - Handles all `click.echo` calls for text output
   - Signature: `_format_stats_text(page_count: int, interest_count: int, tag_count: int, tagged_count: int, interests: list, storage_bytes: int) -> None`

The JSON branch (L759–768) is already compact (10 lines) and can stay inline.

After extraction, `stats` body drops to ~25 lines of data gathering + dispatch.

## Dependencies
- `os` module — already imported at top of cli.py
- `json` module — already imported at top of cli.py
- No cross-module dependencies needed for the extracted helpers

## Status: RESOLVED (verified against code, cycle 1)
