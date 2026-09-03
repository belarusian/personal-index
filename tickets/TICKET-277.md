# TICKET-277: analytics.py load() crashes on non-dict JSON

- Status: RESOLVED
- Module: personal_index/analytics.py
- File: personal_index/analytics.py

## Symptom
`AnalyticsTracker.load(path)` raises `AttributeError` when the JSON file contains a
valid-JSON-but-wrong-type value (null / number / list / string) instead of the dict
that `save()` writes.

## Evidence
- Writer: line 265 `json.dump(data, f, indent=2)` where `data` is a **dict** with keys
  `search_events` and `crawl_events` (lines 241-264).
- Loader: line 275 `data = json.load(f)`; line 277 `for item in data.get("search_events", [])`.
  A non-dict `data` has no `.get` -> `AttributeError`. No try/except wraps the load.
- Contract: `load() -> int` ("Returns total events loaded"); missing file -> `return 0`
  (lines 270-272).

## Minimal additive fix
After `data = json.load(f)`, add:
    if not isinstance(data, dict):
        return 0
This matches the existing missing-file degrade path (count loaded = 0).

## Regression tests (tests/test_analytics.py, TestAnalyticsTrackerNonDictGuard)
- null, number, list, valid-dict-still-works, valid-after-invalid-not-suppressed.

## Issue
Issue: #382
