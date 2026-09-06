# TICKET-528: ContentAPI._search_content docstring + pinning test

Status: RESOLVED
File: personal_index/content_api.py
Symptom: ContentAPI._search_content (def at line 244) has no docstring, so its
  exact dispatch contract is undocumented. Sibling dispatch methods
  (_create/_get/_list/_update/_delete) all carry exact-contract docstrings +
  pinning tests; _search_content is the next un-documented dispatch method.

Evidence (verified in code + TestSearch):
  - q = params.get("q", [""])[0]
  - if not q -> return 400, {"error": "Search query parameter 'q' is required"}
  - else: q_lower = q.lower(); for each item in self._store.values(),
    text = f"{item.get('title','')} {item.get('description','')}".lower();
    if q_lower in text: results.append(item)
  - return 200, {"results": results, "total": len(results), "query": q}
  TestSearch pins: basic -> 200 total==1; no query -> 400; no results -> total==0.

Minimal additive fix:
  - Add a docstring to _search_content stating the exact dispatch contract
    (q read, empty -> 400 required error, case-insensitive substring match
    against title+description, 200 results/total/query shape).
  - Add pinning test TestSearchContentDocstring528 mirroring
    TestDeleteContentDocstring527, asserting key phrases present
    (q, required, 400, results, total, query, 200).

Issue: #927
