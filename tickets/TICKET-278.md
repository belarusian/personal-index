# TICKET-278: session.py load_session() crashes on non-dict JSON

- Status: RESOLVED
- Module: personal_index/session.py
- File: personal_index/session.py

## Symptom
`SessionManager.load_session(filepath)` raises `TypeError` when the JSON file contains a
valid-JSON-but-wrong-type value (null / number / list / string) instead of the dict
that `save_session()` writes via `session.to_dict()`.

## Evidence
- Writer: line 279 `json.dump(session.to_dict(), f, indent=2, default=str)` where
  `CrawlSession.to_dict()` (line 148) returns a **dict** with keys `session_id`, `name`,
  `status`, `started_at`, `completed_at`, `duration`, `stats`, `config`, `metadata`.
- Loader: line 295 `data = json.load(f)`; line 296 `session = CrawlSession(session_id=data["session_id"], ...)`.
  A non-dict `data` (null/number/list/string) has no `__getitem__` for a str key -> `TypeError`.
  No try/except wraps the load.
- Contract: `load_session(filepath) -> CrawlSession | None` ("or None if not found");
  missing file -> `return None` (lines 293-294).

## Minimal additive fix
After `data = json.load(f)`, add:
    if not isinstance(data, dict):
        return None
This matches the existing missing-file degrade path (return None).

## Regression tests (tests/test_session.py, TestSessionManagerNonDictGuard)
- null, number, list, valid-dict-still-works, valid-after-invalid-not-suppressed.

## Issue
Issue: #384
