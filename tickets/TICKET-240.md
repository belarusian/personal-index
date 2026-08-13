# TICKET-240: Extract file-expansion and stats-printing helpers from `cli.pipeline`

## Title
`cli.pipeline` (L644, 83 lines) mixes file expansion, pipeline dispatch, and two separate stats-printing blocks — extract private helpers

## Evidence
`personal_index/cli.py`, lines 644–726. The function performs 8 distinct operations:

| Lines | Operation |
|-------|-----------|
| 663 | Resolve `data_dir` |
| 666–671 | Build `PipelineConfig` |
| 673–676 | Build `PipelineRunner` |
| 680–691 | **Expand import files** — recursive `os.walk` with extension filter |
| 692–700 | Dispatch: files vs URLs vs error |
| 702–715 | **Print pipeline stage stats** — 10 `click.echo` calls |
| 717–723 | **Print index/tag/interest store stats** — opens 3 stores, 4 `click.echo` calls |
| 726 | `finally: runner.close()` |

The file-expansion block (L680–691) duplicates logic similar to `_collect_files` (L321) but with a different extension set (adds `.xml`, `.json`). The two stats-printing blocks are self-contained and could be private helpers.

## Impact
- 83-line function is hard to test in isolation
- File expansion logic is duplicated (differs from `_collect_files` in extension set)
- Stats printing is not reusable from other commands

## Suggestion
Extract three private helpers:

1. **`_expand_import_files(import_files: list[str], recursive: bool) -> list[str]`**
   - Move L680–691 into this function
   - Consider unifying with `_collect_files` or documenting the extension-set difference

2. **`_print_pipeline_stats(stats: PipelineStats) -> None`**
   - Move L702–715 into this function
   - Takes the `stats` object returned by `runner.run()` / `runner.run_from_files()`

3. **`_print_index_stats(data_dir: str) -> None`**
   - Move L717–723 into this function
   - Opens `get_search_index`, `get_tag_store`, `get_interest_store` internally

After extraction, `pipeline` body drops to ~30 lines of orchestration.

## Dependencies
- `PipelineStats` type from `personal_index.pipeline_runner` (already imported via `runner`)
- `get_search_index`, `get_tag_store`, `get_interest_store` — already used in cli.py
