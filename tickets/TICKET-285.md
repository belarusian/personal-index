# TICKET-285: search_suggestions _get_trending_counts keys Counter by (query, score) tuples

- Status: RESOLVED
- Issue: #394
- Module: personal_index/search_suggestions.py
- Class: logic (Counter keyed by composite (query, int(score)) tuples instead of query)

## Symptom
`SearchSuggestions._get_trending_counts` (line 159) builds a Counter keyed by
`(entry.query, int(self._apply_decay(entry)))` tuples (lines 161-163). A Counter is meant
to count occurrences of a single key; keying by (query, score) means the same query with a
different decayed score becomes a DIFFERENT key, so the count never aggregates and the
"counts" are meaningless (each tuple appears at most once). The method is documented as
"Get trending counts as a Counter for backward compatibility" — the natural key is the
query string.

## Evidence
- personal_index/search_suggestions.py:159  `def _get_trending_counts(self) -> Counter:`
- personal_index/search_suggestions.py:161  `return Counter(`
- personal_index/search_suggestions.py:162  `(entry.query, int(self._apply_decay(entry)))`  <- composite tuple key
- personal_index/search_suggestions.py:163  `for entry in self._trending.values()`

## Minimal additive fix
- Key the Counter by the query string only: `Counter(entry.query for entry in self._trending.values())`.

## Regression tests (tests/test_search_suggestions.py)
- _get_trending_counts aggregates repeated queries under a single string key.
