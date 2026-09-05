# TICKET-392: _try_process_batch placeholder docstring (class-(b) doc-drift)

**File:** personal_index/content_batch.py
**Line:** 181
**Symptom:** Docstring `"""Try to process a single batch with retries."""` is a
placeholder that does not state the actual behavior: it does not describe the
retry loop `for attempt in range(max_retries)`, that on success it extends
`result.output` with the processor output and increments `result.processed` by
`len(batch)`, or that on final failure (after exhausting retries) it increments
`result.failed` by `len(batch)` and appends an error dict
(`batch_start`, `attempts`, `error`) to `result.errors`.

**Evidence:** Line 181: `"""Try to process a single batch with retries."""`
The body (lines 182-196) performs: `for attempt in range(max_retries)`; on
success `result.output.extend(output)` + `result.processed += len(batch)` +
`break`; on `ValueError` when `attempt == max_retries - 1`,
`result.failed += len(batch)` and `result.errors.append({...})`.

**Minimal additive fix:** Reword the docstring to enumerate the exact
sub-components the body performs (the retry loop, the success side effects on
result.output/result.processed, and the final-failure side effects on
result.failed/result.errors). Add ONE pinning behavior test that witnesses the
corrected claim by asserting on the modified `BatchResult` object for a success
path (output extended, processed incremented) and a final-failure path (failed
incremented, error dict appended).

**Status:** OPEN
**Issue:** #622
