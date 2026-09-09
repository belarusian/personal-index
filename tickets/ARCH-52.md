# ARCH-52: content-batch — only `ValueError` is caught, so any other processor exception aborts the whole run

Status: OPEN
Component: `personal_index/content_batch.py`
Issue: #1156
Refs: ARCH-2 (#983 umbrella)

## Symptom

`BatchProcessor` advertises "support for error handling" (module docstring)
and exposes three public entry points — `process`, `process_with_retry`, and
`process_item_by_item` — each of which is supposed to isolate failures so a
bad batch/item does not sink the whole run. But every one of them catches
**only `ValueError`**:

- `_process_single_batch` wraps `self.processor(batch)` in
  `try: ... except ValueError as e:`.
- `_try_process_batch` (used by `process_with_retry`) retries only on
  `except ValueError`.
- `_process_single_item` (used by `process_item_by_item`) catches only
  `except ValueError as e:`.

Consequently a processor that raises any other exception type — `KeyError`,
`TypeError`, `IndexError`, `AttributeError`, a domain error, … — propagates
out of the public method. The whole run aborts: no `BatchResult` is returned,
no error is recorded, and the partially-accumulated `result` (already-processed
batches, `started_at`, progress) is lost. This defeats the module's stated
purpose and breaks the invariant a caller would reasonably expect,
`processed + failed == total_items`, for any non-`ValueError` failure.

This is the single most important hole: the error-handling contract is
narrower than the module's own description, and the failure mode (silent
total abort) is the worst possible one for a batch processor.

## Public contract (the fix must preserve the happy path)

- All public methods keep their current signatures and behavior:
  `BatchResult` (fields, `success_rate`, `to_dict`), and
  `BatchProcessor.__init__` / `process` / `process_with_retry` /
  `process_item_by_item`, plus the private `_process_single_batch` /
  `_try_process_batch` / `_process_single_item` / `_finalize_result` /
  `_default_processor`.
- The happy path is unchanged: a processor that succeeds returns the same
  `BatchResult` (same `batch_id` scheme, `processed == total_items`,
  `failed == 0`, `output` extended in order, `on_progress` called per
  batch/item, `completed_at`/`duration_seconds` finalized).
- The error-handling contract must be widened and stated explicitly (pick one
  and state it in the `BatchProcessor` docstring + `docs/content-batch.md`):
  - **Option A (catch `Exception`):** each per-batch / per-item handler
    catches `Exception` (not just `ValueError`) and records a failure the same
    way it records a `ValueError` (same error-dict shape: `batch_start` /
    `batch_size` / `error`, or `batch_start` / `attempts` / `error`, or
    `item_index` / `item_id` / `error`). `processed + failed == total_items`
    then holds for any processor exception. `KeyboardInterrupt` /
    `SystemExit` (BaseException, not Exception) still propagate.
  - **Option B (document the narrow contract):** keep catching only
    `ValueError` and state explicitly in the `BatchProcessor` docstring and
    `docs/content-batch.md` that ONLY `ValueError` is isolated — any other
    exception type propagates and aborts the run — so a caller knows to wrap
    its processor to raise `ValueError` (or to catch other types itself).
- Whichever option is chosen, the postcondition must hold and be stated: a
  caller reading the `BatchProcessor` docstring must know, without reading the
  source, which exception types are isolated into `result.errors` and which
  abort the run.

## Acceptance criteria

1. The happy path is unchanged: a succeeding processor yields the same
   `BatchResult` (batch_id scheme, `processed == total_items`, `failed == 0`,
   ordered `output`, per-batch/item `on_progress` calls, finalized
   `completed_at`/`duration_seconds`) as before.
2. The set of exception types that are isolated into `result.errors` (vs.
   propagated) is stated in the `BatchProcessor` docstring and in
   `docs/content-batch.md` (Option A: any `Exception` is isolated; Option B:
   only `ValueError` is isolated and all other types propagate).
3. Under Option A: a processor raising a non-`ValueError` (e.g. `KeyError`)
   on one batch/item records a failure with the same error-dict shape as a
   `ValueError`, the run continues to the remaining batches/items, and
   `processed + failed == total_items`; `KeyboardInterrupt`/`SystemExit`
   still propagate.
4. Under Option B: the docstring and docs page both state that only
   `ValueError` is isolated and that any other exception type propagates and
   aborts the run, and no caller-facing API implies broader isolation.

## Pinning tests to add (tests/test_content_batch.py)

- `test_process_happy_path` — a succeeding processor over a multi-batch input
  returns `processed == total_items`, `failed == 0`, ordered `output`, and
  `on_progress` called once per batch; pins the current clean behavior so the
  fix does not change it.
- `test_non_valueerror_isolation` (the contract hole) — a processor that
  raises `KeyError` on one batch: under Option A the run continues, the
  failing batch is recorded in `result.errors` (same shape as a `ValueError`
  entry), `processed + failed == total_items`, and a `BatchResult` is
  returned; under Option B the test asserts the docstring states only
  `ValueError` is isolated and that `KeyError` propagates (asserted via
  `pytest.raises`). This single test pins the whole contract hole.
- `test_process_item_by_item_non_valueerror` (guard path) — the same
  non-`ValueError` case through `process_item_by_item`, pinning that the
  per-item handler isolates (Option A) or propagates (Option B) consistently
  with the batch handlers, and that the error dict is keyed
  `item_index`/`item_id`/`error`.

## Docs update (same PR)

`docs/content-batch.md` "Contract holes" section (already authored in this
PR) names this as the primary hole; the implementer must update the
`BatchProcessor` entry in the "Public API" section to state the chosen
exception-isolation contract once implemented.
