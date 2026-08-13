# TICKET-003: Duplicate run_from_files across 3 modules

**Files:**
- `personal_index/pipeline_runner.py:235` — `run_from_files` → PipelineStats
- `personal_index/pipeline_orchestrator.py:195` — `run_from_files` → PipelineResult
- `personal_index/pipeline_e2e.py:133` — `run_from_files` → PipelineRunResult

**Severity:** Medium

## Evidence

Three classes implement `run_from_files()` with different return types and overlapping logic. Each reads files, runs pipeline stages, and returns results — but the implementations diverge in error handling and return structure.

## Suggestion

Extract shared file-reading + pipeline logic into a base class or utility. Each subclass handles its specific return type and error strategy.

## Actionable

Yes — but deferred. These serve different entry points (CLI, orchestrator, E2E tests). Not a quick win.
