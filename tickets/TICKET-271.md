# TICKET-271: progress.py non-dict JSON guard

- Status: RESOLVED
- Module: personal_index/progress.py
- Class: json.load non-dict guard sweep (9th instance)

## Symptom
`ProgressTrackerStore.load_all()` (line ~263) calls `data = json.load(f)`
(line ~271) then `for oid, d in data.items()`. A non-dict JSON value
(null / list / number) crashes with `AttributeError` before any tracker is
loaded and before the count is returned.

## Evidence (reproduced live)
- null    -> AttributeError: 'NoneType' object has no attribute 'items'
- [1,2,3] -> AttributeError: 'list' object has no attribute 'items'
- 42      -> AttributeError: 'int' object has no attribute 'items'

## Writer type
`ProgressTrackerStore.save_all()` (line ~251) writes
`json.dump(data, f, indent=2)` where data is a **dict**
`{oid: tracker.to_dict()}`. Guard expected type = dict.

## Loader return shape
`load_all` returns an **int count** (`return len(self._trackers)` on the happy
path). On a bad file the safe default is `0` (nothing loaded). Do NOT leave
partial trackers; a plain `return 0` is correct (no per-field reset needed).

## Minimal additive fix
Immediately after `data = json.load(f)`, add:
    if not isinstance(data, dict):
        return 0

## Tests
3 regression tests (null / list / number) in tests/test_progress.py,
mirroring the established pattern (store pointed at a tmp_path file, call
load_all, assert count == 0).

## Issue: #371 (closed)

## Resolution
- Branch build26/progress-json-guard, PR #372, squash-merged 683d1a7 to main, CI green (3 jobs), gh #371 closed.
- 3 regression tests added (null/list/number).
