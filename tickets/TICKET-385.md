# TICKET-385: content_batch.py placeholder docstrings (class-(b) doc-drift)

Status: OPEN

## File
personal_index/content_batch.py

## Symptom
Five methods carry placeholder "Process <name>." docstrings that do not
describe the behavior the body actually performs:
- BatchProcessor.process (line 87)
- BatchProcessor._process_single_batch (line 115)
- BatchProcessor.process_with_retry (line 133)
- BatchProcessor.process_item_by_item (line 199)
- BatchProcessor._process_single_item (line 218)

## Evidence
- L87: `"""Process all items in batches."""` — body increments `_batch_counter`,
  builds a BatchResult (batch_id/total_items/started_at), chunks items by
  `batch_size`, runs each chunk through `_process_single_batch`, reports
  progress via `on_progress`, finalizes timing, returns the result.
- L115: `"""Process a single batch, catching ValueError on failure."""` — body
  runs `self.processor(batch)`; on success extends `output` and
  `processed += len(batch)`; on ValueError `failed += len(batch)` and appends
  an error entry keyed by `batch_start`/`batch_size`/`error`.
- L133: `"""Process items with retry logic for failed batches."""` — body is
  like `process` but each chunk goes through `_try_process_batch`, which retries
  up to `max_retries` before recording a failure.
- L199: `"""Process items individually with per-item error handling."""` — body
  processes each item individually via `item_processor` (not batched),
  accumulating per-item output/processed/failed/errors, reporting progress per
  item, finalizing timing, returning the result.
- L218: `"""Process a single item with error handling."""` — body runs
  `processor(item)`; on success appends output and `processed += 1`; on
  ValueError `failed += 1` and appends an error entry keyed by
  `item_index`/`item_id`/`error`.

## Minimal additive fix
Reword each docstring to state the exact behavior the body performs, and add
ONE behavior test pinning the corrected `_process_single_batch` claim (on
ValueError the error entry is keyed by `batch_start`/`batch_size`, not
`item_index`) against the returned BatchResult.

## Issue
Issue: #608
