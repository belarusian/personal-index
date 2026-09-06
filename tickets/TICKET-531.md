# TICKET-531: ContentAPI._get_stats docstring + pinning test

Status: OPEN
File: personal_index/content_api.py
Symptom: ContentAPI._get_stats (def at line 287) has no docstring, so its
  exact dispatch contract is undocumented. Sibling dispatch methods
  (_create/_get/_list/_update/_delete/_search_content/_export_content/
  _health_check) all carry exact-contract docstrings + pinning tests;
  _get_stats is the last un-documented dispatch method.

Evidence (verified in code + TestStats):
  - return 200, {"total_items": len(self._store), "tags": self._collect_tags()}
  - No params read; reads only self._store (via len) and _collect_tags().
  - _collect_tags() returns dict[str, int] counting each tag across items.
  TestStats pins: GET /api/v1/stats -> 200, body["total_items"]==2,
  body["tags"]["a"]==1.

Minimal additive fix:
  - Add a docstring to _get_stats stating the exact dispatch contract
    (no params, 200 total_items/tags shape, tags is a tag->count mapping).
  - Add pinning test TestGetStatsDocstring531 mirroring
    TestHealthCheckDocstring530, asserting key phrases present
    (total_items, tags, 200).

Issue: #935
