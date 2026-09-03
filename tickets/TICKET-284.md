# TICKET-284: _get_trending_counts keys Counter by (query, score) tuples and truncates decay

Status: RESOLVED
Module: personal_index/search_suggestions.py (SearchSuggestions._get_trending_counts)
- Issue: #394

## Symptom
The method is documented as "trending counts as a Counter for backward
compatibility", but lines 159-164 build
    Counter((entry.query, int(self._apply_decay(entry))) for entry in ...)
so the KEYS are (query, decayed-score) tuples, not query strings, and the
COUNT is always 1. Two independent bugs:
  a) any consumer doing counts[query] or most_common() over query strings gets
     nothing useful (its documented backward-compat contract is broken);
  b) int() truncates every decayed score below 1.0 to 0, so a decayed entry
     contributes zero instead of its fractional weight.

## Evidence (runtime repro, confirmed by probe)
    s = SearchSuggestions()
    for q in ["python", "python", "rust"]: s.record_search(q)
    c = s._get_trending_counts()
    dict(c)          -> {("python", 1): 1, ("rust", 0): 1}   # tuple keys, count 1
    c["python"]      -> 0                                     # lookup by query fails
    c.most_common()  -> [(("python", 1), 1), (("rust", 0), 1)]
    # decay truncation: entry with decayed score 2.38e-15 -> int() == 0

## Minimal additive fix
Key by query and accumulate the (float) decayed score:
    counts: Counter = Counter()
    for entry in self._trending.values():
        counts[entry.query] += self._apply_decay(entry)
    return counts
Keep the return type Counter. If integer counts are required by a caller,
round at the call site - do not truncate per entry.

## Regression tests to add
1. counts[query] is non-zero for a recorded query (lookup by string works).
2. repeated recordings of the same query accumulate (>= 2 for two records with
   decay_half_life <= 0).
3. a decayed entry still contributes a positive fractional score (no int
   truncation to 0).

## Resolution (cycle 29)
Fixed on branch build29/search-suggestions-fixes (no git remote in this sandbox -> no gh issue; Issue: LOCAL-NONE). Local gate green (pytest 5198 passed / 22 skipped; ruff clean; mypy 495 files). Regression tests added in tests/test_search_suggestions.py.

## Reconciliation addendum (cycle 31)
Renumbered from local TICKET-261 (collided with a DIFFERENT upstream ticket of the same
number). The earlier "no git remote / Issue: LOCAL-NONE" note is stale: origin exists
and this work is tracked upstream as the Issue above, landed via the reconcile/main-31 PR.
