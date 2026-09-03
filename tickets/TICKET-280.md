# TICKET-280: publish_dashboard.py unguarded json.loads keyed access

- Status: OPEN
- Module: personal_index/publish_dashboard.py
- Class: non-dict JSON guard (json.loads -> keyed .get access, no guard)

## Symptom
`validate_sync()` and `_git_commit_push()` call `json.loads(...)` then immediately
perform keyed access (`.get("summary", {})`) with no `isinstance` guard and no
try/except. If the codemap JSON or embedded metadata is a non-dict (null / number /
list / string), `.get` raises `AttributeError` and the publish/validate flow crashes.

## Evidence
- personal_index/publish_dashboard.py:63  `codemap = json.loads(json_path.read_text(...))`
- personal_index/publish_dashboard.py:64  `json_summary = codemap.get("summary", {})`   <- unguarded keyed access
- personal_index/publish_dashboard.py:76  `embedded = json.loads(htmlmod.unescape(embedded_raw))`
- personal_index/publish_dashboard.py:77  `embedded_summary = embedded.get("summary", {})` <- unguarded keyed access
- personal_index/publish_dashboard.py:149 `summary = json.loads(json_path.read_text(...)).get("summary", {})` <- unguarded chained access

## Writer type (verified)
docs_generator.generate_metadata_json() (personal_index/docs_generator.py:424-457)
persists a **dict** with a top-level `summary` key. Expected type = dict.

## Loader degrade contract (verified)
validate_sync() returns a dict: `{"sync": True, "summary": ...}` on success,
`{"sync": False, "reason": ...}` / `{"sync": False, "mismatches": ...}` on failure.
_git_commit_push() uses summary only to build a commit message (defaults '?').

## Minimal additive fix
- After line 63: `if not isinstance(codemap, dict): return {"sync": False, "reason": "codemap JSON is not an object"}`
- After line 76: `if not isinstance(embedded, dict): return {"sync": False, "reason": "embedded metadata is not an object"}`
- Line 149: guard the chained access so a non-dict yields `{}` (summary defaults to '?').

## Tests
Add to tests/test_publish_dashboard.py (TestValidateSync + a new TestCommitSummaryGuard):
null, number, list (dict-expected), valid-still-works, valid-after-invalid-not-suppressed.

## Issue
Issue: #388
