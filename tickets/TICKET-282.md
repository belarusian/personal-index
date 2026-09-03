# TICKET-282: trending suggestions silently drop every mixed-case query

Status: RESOLVED
Module: personal_index/search_suggestions.py (SearchSuggestions._suggest_from_trending)
- Issue: #392

## Symptom
`record_search()` keys the trending store by `query.lower()` but keeps the
caller's original casing in `TrendingEntry.query` (lines ~131-137).
`_suggest_from_trending` then compares the lowercased prefix against the
ORIGINAL-cased text: `if query.startswith(prefix):` (line 305). `suggest()`
lowercases its argument (line ~184), so any recorded query containing an
uppercase character can never prefix-match and never appears as a trending
suggestion - a silent false negative for ordinary input ("Python Tips").

## Evidence (runtime repro, confirmed by probe)
    s = SearchSuggestions(); s.record_search("Python Tips")
    s.suggest("py", sources=["trending"])             -> []               # WRONG
    s.suggest("py", sources=["trending"], fuzzy=True) -> ["Python Tips"]  # only via fuzzy
    t = SearchSuggestions(); t.record_search("python tips")
    t.suggest("py", sources=["trending"])             -> ["python tips"]  # control

Existing test `test_suggest_from_trending` passes only because it records the
already-lowercase "python" (tests/test_search_suggestions.py ~210-216).

## Minimal additive fix
Compare case-insensitively in the trending source, mirroring history/tags/
keywords (which all use `x.lower().startswith(prefix)`):
    if query.lower().startswith(prefix):
Keep `Suggestion.text` as the stored original text (display casing preserved).

## Regression tests to add (tests/test_search_suggestions.py)
1. mixed-case recorded query IS returned for a lowercase prefix (exact-prefix,
   fuzzy=False).
2. returned text preserves the original casing.

## Resolution (cycle 29)
Fixed on branch build29/search-suggestions-fixes (no git remote in this sandbox -> no gh issue; Issue: LOCAL-NONE). Local gate green (pytest 5198 passed / 22 skipped; ruff clean; mypy 495 files). Regression tests added in tests/test_search_suggestions.py.

## Reconciliation addendum (cycle 31)
Renumbered from local TICKET-259 (collided with a DIFFERENT upstream ticket of the same
number). The earlier "no git remote / Issue: LOCAL-NONE" note is stale: origin exists
and this work is tracked upstream as the Issue above, landed via the reconcile/main-31 PR.
