# TICKET-232: Refactor `run` and `run_from_files` in pipeline_orchestrator.py (71L + 69L → shared core)

## What's Wrong

`personal_index/pipeline_orchestrator.py` has two oversized methods that are near-duplicates:

- `run` (line 187, 71 lines) — crawls URLs then runs filter/score/tag/index
- `run_from_files` (line 282, 69 lines) — reads files then runs filter/score/tag/index

Both exceed the 50-line limit. More importantly, they share ~50 lines of identical code (stages 2–5 of `run` = stages 2–5 of `run_from_files`).

## Evidence

Reading lines 187–258 and 282–351 of `personal_index/pipeline_orchestrator.py`:

Both functions follow this identical skeleton:
