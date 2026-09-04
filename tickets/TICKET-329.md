# TICKET-329 — content_batch module docstring over-promises "parallel execution"

Status: RESOLVED
Class: (b) doc/behavior drift
Module: personal_index/content_batch.py

## Symptom
The module docstring promises a capability the code does not implement.

## Evidence
- `personal_index/content_batch.py` line 4 (module docstring):
  "with support for parallel execution, error handling, and progress tracking."
- No concurrency primitive exists anywhere in the module:
  - imports are only `Callable`, `dataclass`, `field`, `datetime`, `timezone`, `Any`
    (lines 10-13) — no `concurrent.futures`, `threading`, `multiprocessing`, or `asyncio`.
  - `BatchProcessor.process()` (line 84) is a plain sequential loop:
    `for i in range(0, total, self.batch_size):` then `_process_single_batch(...)`.
  - A grep for thread/process/concurrent/parallel/executor/multiprocess/asyncio
    matches only line 4 (the docstring) plus incidental "processed" words.
- The class docstring (lines 67-71) is accurate: "custom processing functions,
  error handling, and progress callbacks" — it makes NO parallel claim. So the
  over-promise is isolated to the module docstring.

## Minimal additive fix
Correct the module docstring line 4 to drop "parallel execution", e.g.:
"with support for error handling and progress tracking." (the two capabilities
that are actually implemented). Add ONE regression test
`TestModuleDocstringContract::test_docstring_does_not_promise_parallel_execution`
asserting "parallel" is absent from `module.__doc__`.

## Issue: #496
