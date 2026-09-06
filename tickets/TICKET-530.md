# TICKET-530: ContentAPI._health_check docstring + pinning test

Status: OPEN
File: personal_index/content_api.py
Symptom: ContentAPI._health_check (def at line 276) has no docstring, so its
  exact dispatch contract is undocumented. Sibling dispatch methods
  (_create/_get/_list/_update/_delete/_search_content/_export_content) all
  carry exact-contract docstrings + pinning tests; _health_check is the next
  un-documented dispatch method.

Evidence (verified in code + TestHealth):
  - return 200, {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
  - No params read; no store access.
  TestHealth pins: GET /api/v1/health -> 200, body["status"]=="healthy".

Minimal additive fix:
  - Add a docstring to _health_check stating the exact dispatch contract
    (no params, 200 status/healthy/timestamp shape, timestamp is a UTC
    ISO-8601 string).
  - Add pinning test TestHealthCheckDocstring530 mirroring
    TestExportContentDocstring529, asserting key phrases present
    (status, healthy, timestamp, 200).

Issue: #931
