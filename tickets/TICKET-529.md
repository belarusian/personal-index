# TICKET-529: content_health.HealthReport class docstring "indexed content" over-promise

Status: OPEN
Issue: #934
Module: personal_index/content_health.py
Class: HealthReport
Type: (b) doc-drift (docstring over-promise)

## Symptom
The `HealthReport` class docstring (line 79) reads:
    "Overall health report for all indexed content."
The phrase "indexed content" names a data SOURCE the code never touches.

## Evidence
- `HealthReport` is a dataclass with fields `total_items`, `healthy_count`, etc., initialized with defaults or via direct construction.
- No `__init__` takes an index/store handle; the class is populated by `ContentHealthChecker._build_report(results)` which aggregates `HealthCheckResult` objects passed in via `check_item`/`check_all`.
- The class never accesses an index, store, or crawler; it is a pure data container for check results supplied by the caller.
- The docstring over-promises a source ("indexed content") the code does not use.

## Minimal additive fix
Reword the class docstring to state the exact mechanism the body performs:
    "Overall health report aggregating results from checked content items."
Add ONE behavior test pinning the corrected claim against the returned object:
a fresh `HealthReport` can be constructed with arbitrary counts and `summary()` formats them correctly, and `HealthReport` built via `ContentHealthChecker.check_all` reflects only the items explicitly passed to `check_item`, not an implicit index.
