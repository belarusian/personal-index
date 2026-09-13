# Batch processing (`personal_index.content_batch`)

Status: **spec** — audited against current code (cycle 215).

`BatchProcessorFn = Callable[[list[dict[str, Any]]], list[dict[str, Any]]]`
(module-level type alias for the batch processor signature).

## BatchResult
`@dataclass` with fields: `batch_id: str`, `total_items: int`,
`processed: int = 0`, `failed: int = 0`, `errors: list[dict[str, Any]] = []`,
`started_at: datetime | None = None`, `completed_at: datetime | None = None`,
`duration_seconds: float = 0.0`, `output: list[dict[str, Any]] = []`.

- `success_rate` (property) -> `float` — **Guard path:** when
  `total_items == 0` returns `0.0` (no division by zero); otherwise
  `processed / total_items` (raw float, NOT rounded).
- `to_dict() -> dict[str, Any]` — returns a NEW dict with exactly nine keys:
  `batch_id`, `total_items`, `processed`, `failed`, `errors` (passed through
  by reference, NOT copied), `started_at` / `completed_at` (each
  `.isoformat()` when set, else `None`), `duration_seconds`, and
  `success_rate` (`round(self.success_rate, 4)`). No guard path; no side
  effects.

## BatchProcessor
`BatchProcessor(batch_size: int = 100, processor: BatchProcessorFn | None =
None, on_progress: Callable[[int, int], None] | None = None)`. `processor`
defaults to `_default_processor` (returns items unchanged) when `None`;
`on_progress` is called as `on_progress(processed_count, total)` after each
batch/item. An internal `_batch_counter` (starts 0) is incremented once per
public `process*` call and used to build `batch_id = f"batch-{counter}"`.

- `process(items: list[dict[str, Any]]) -> BatchResult` — chunks `items` by
  `batch_size` (last chunk may be shorter), runs each chunk through
  `_process_single_batch`, reports progress per chunk, then
  `_finalize_result` (stamps `completed_at` and `duration_seconds` from
  `started_at`). Returns the `BatchResult`. **Error handling:** any
  `Exception` raised by the processor is caught (per batch) and isolated
  into `result.errors`; `KeyboardInterrupt` / `SystemExit`
  (`BaseException`) still propagate out of `process`.
- `process_with_retry(items: list[dict[str, Any]], max_retries: int = 3) ->
  BatchResult` — same chunking/progress/finalize as `process`, but each chunk
  goes through `_try_process_batch`, which retries the processor up to
  `max_retries` times; an `Exception` on the final attempt records a failure
  (error dict keyed `batch_start`, `attempts`, `error`). **Error handling:**
  any `Exception` is retried/caught; `BaseException` propagates.
- `process_item_by_item(items: list[dict[str, Any]], item_processor:
  Callable[[dict[str, Any]], dict[str, Any]]) -> BatchResult` — runs each item
  individually (NOT batched) through `_process_single_item`, reports progress
  per item, finalizes, returns the `BatchResult`. **Error handling:** any
  `Exception` raised by `item_processor` is caught (per item) and isolated
  into `result.errors`; `BaseException` still propagates out of
  `process_item_by_item`.

### Private helpers (documented for the error-handling contract)
- `_process_single_batch(batch, batch_start, result)` — on success extends
  `result.output` with the processor output and `result.processed +=
  len(batch)`; on any `Exception` `result.failed += len(batch)` and appends
  an error dict keyed `batch_start`, `batch_size`, `error`.
- `_try_process_batch(batch, max_retries, batch_start, result)` — `for
  attempt in range(max_retries)`: on success extends `result.output`,
  `result.processed += len(batch)`, breaks; on any `Exception` at the final
  attempt `result.failed += len(batch)` and appends an error dict keyed
  `batch_start`, `attempts`, `error`.
- `_process_single_item(item, idx, processor, result)` — on success appends
  the processor output to `result.output` and `result.processed += 1`; on
  any `Exception` `result.failed += 1` and appends an error dict keyed
  `item_index`, `item_id` (`item.get("id", "unknown")`), `error`.
- `_finalize_result(result)` — sets `completed_at = now(utc)` and, when
  `started_at` is set, `duration_seconds = (completed_at - started_at).
  total_seconds()`.
- `_default_processor(items)` — returns `items` unchanged.

## Contract holes
- **Resolved (ARCH-52): any `Exception` is now isolated.** All three public
  entry points (`process`, `process_with_retry`, `process_item_by_item`)
  catch any `Exception` from the processor and record it in `result.errors`
  (same error-dict shape as before), so the run continues and
  `processed + failed == total_items` holds for any processor exception.
  `KeyboardInterrupt` / `SystemExit` (`BaseException`, not `Exception`)
  still propagate and abort the run. Previously only `ValueError` was
  caught, so any other exception type (`KeyError`, `TypeError`,
  `IndexError`, …) propagated out of the public method and aborted the
  entire run (ticketed as ARCH-52).
