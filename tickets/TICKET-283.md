# TICKET-283: to_dict/from_dict alias live lists - restored instances share mutable state

Status: RESOLVED
Module: personal_index/search_suggestions.py (SearchSuggestions.to_dict / from_dict)
- Issue: #393

## Symptom
`to_dict()` returns the LIVE internal lists under "search_history"/"tags"/
"keywords" (lines 375-377) instead of copies, and `from_dict()` assigns
`data.get("search_history", [])` etc. directly onto the instance (lines
385-387). Consequences:
  a) a caller mutating the dict it just got back mutates the live object;
  b) two instances restored from the SAME dict share one list object, so a
     `record_search` on one silently appears in the other (and in the source).

## Evidence (runtime repro, confirmed by probe)
    a = SearchSuggestions(); a.add_search_history(["alpha"])
    d = a.to_dict(); d["search_history"].append("INJECTED")
    a._search_history -> ["alpha", "INJECTED"]          # caller mutated the live object
    b = SearchSuggestions.from_dict(d); c = SearchSuggestions.from_dict(d)
    b.record_search("ONLY_IN_B")
    c._search_history -> ["alpha", "INJECTED", "ONLY_IN_B"]   # cross-instance leak

Existing `test_from_dict_roundtrip` compares values only, so it never sees the
shared identity.

## Minimal additive fix
Copy on the way out and on the way in (no behaviour change for readers):
    "search_history": list(self._search_history),   # and tags, keywords
    instance._search_history = list(data.get("search_history", []))   # and tags, keywords

## Regression tests to add
1. mutating the dict returned by to_dict() does not change the source object.
2. two instances from_dict()'d from one dict are independent after a
   record_search on one of them.

## Resolution (cycle 29)
Fixed on branch build29/search-suggestions-fixes (no git remote in this sandbox -> no gh issue; Issue: LOCAL-NONE). Local gate green (pytest 5198 passed / 22 skipped; ruff clean; mypy 495 files). Regression tests added in tests/test_search_suggestions.py.

## Reconciliation addendum (cycle 31)
Renumbered from local TICKET-260 (collided with a DIFFERENT upstream ticket of the same
number). The earlier "no git remote / Issue: LOCAL-NONE" note is stale: origin exists
and this work is tracked upstream as the Issue above, landed via the reconcile/main-31 PR.
