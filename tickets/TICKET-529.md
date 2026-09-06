# TICKET-529: ContentAPI._export_content docstring + pinning test

Status: RESOLVED
File: personal_index/content_api.py
Symptom: ContentAPI._export_content (def at line 265) has no docstring, so its
  exact dispatch contract is undocumented. Sibling dispatch methods
  (_create/_get/_list/_update/_delete/_search_content) all carry exact-contract
  docstrings + pinning tests; _export_content is the next un-documented
  dispatch method.

Evidence (verified in code + TestExport):
  - fmt = params.get("format", ["json"])[0]
  - items = list(self._store.values())
  - return 200, {"format": fmt, "items": items, "total": len(items)}
  TestExport pins: format=json -> 200, body["format"]=="json", body["total"]==2;
  no format param -> body["format"]=="json" (default).

Minimal additive fix:
  - Add a docstring to _export_content stating the exact dispatch contract
    (format read with default "json", items = all store values, 200
    format/items/total shape).
  - Add pinning test TestExportContentDocstring529 mirroring
    TestSearchContentDocstring528, asserting key phrases present
    (format, json, items, total, 200).

Issue: #929
