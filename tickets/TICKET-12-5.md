# TICKET-12-5: Refactor `pipeline_e2e.PipelineE2E.run_from_files` (54L, line 202)

## What's wrong

`PipelineE2E.run_from_files` in `personal_index/pipeline_e2e.py` (line 202) is 54 lines and processes each file through 5 pipeline stages in a single loop body:
1. **Read + extract** — `_stage_read`, `_stage_extract` with error handling
2. **Filter** — `_stage_filter` with continue on rejection
3. **Score + threshold** — `_stage_score` with min_score_threshold check
4. **Tag** — `_stage_tag` with interest matching
5. **Index** — `_stage_index` with error handling

The loop body interleaves 5 stage calls with counter updates and conditional logic, making it hard to reason about the pipeline flow.

## Suggestion

Extract one private helper:

### Helper: `_process_single_file(self, file_path, result)` -> None
Processes one file through all 5 stages, updating result counters. Keeps the main function as a thin loop over file_paths.

## Signature
```python
def _process_single_file(self, file_path: str, result: PipelineRunResult) -> None:
```
