# TICKET-550: exact-contract docstrings for FacetBuilder.build / aggregate + pinning test

Status: OPEN
Issue: #979

## File
personal_index/search_facets/facet_builder.py

## Symptom
FacetBuilder.build and FacetBuilder.aggregate have terse stub docstrings that omit
the exact contract the code delivers. The existing tests (tests/test_search_facets.py
TestFacetBuilder) pin the happy-path values and the max_values limit but NOT the
non-obvious contract points below, nor the docstring phrases.

## Evidence (verified live against the code)
build (line 24):
- Returns {} when items is empty (line 30-31).
- For each field in facet_fields, values are extracted via _extract_values and each
  value is stringified (str(value)) before add_value (line 44) -- e.g. score 5 -> "5",
  enabled True -> "True".
- A field whose facet ends up with NO values is SKIPPED (not included in the result
  dict) -- the `if not facet.values: continue` at line 47. Verified: build with
  items=[{'tags': []}, {'other':'x'}] and facet_fields=['tags','other'] -> only
  'other' present, 'tags' absent.
- Values are sorted by count descending (facet.sort_values, line 50) and then TRUNCATED
  to the top max_values (line 51) -- so max_values keeps the highest-count values, not
  the first-inserted ones. Verified: counts a=2,b=1,c=1,d=1,e=1 with max_values=3 ->
  [('a',2),('b',1),('c',1)].
- Facet type is resolved via _resolve_facet_type (custom_types by full field name, then
  by base name after the last dot, then DEFAULT_FACET_TYPES by base name, else STRING).

aggregate (line 56):
- The union of keys from both dicts is produced (line 60).
- When a key is present in BOTH dicts, a NEW Facet is built with facet_type taken from
  facets_a (line 65), counts for each value NAME are SUMMED across both facets, and the
  merged values are re-sorted by count descending (line 74). Verified: a={'a':1,'b':2},
  b={'b':1,'c':3} -> [('b',3),('c',3),('a',1)].
- When a key is present in ONLY ONE dict, that facet object is passed through BY
  REFERENCE (not copied) -- lines 77-79. Verified: m['tags'] is f1['tags'] -> True.

## Minimal additive fix
Reword the two docstrings to state the exact contract (empty-items -> {}; value
stringification; empty-facet skip; sort-then-truncate top-N; type resolution order for
build; union-of-keys, summed-counts + re-sort, and pass-through-by-reference for
aggregate). Add a pinning test class asserting key contract fragments appear in the
docstrings (normalized via doc.lower() to avoid case/backtick traps) AND re-pinning the
non-obvious behaviors (empty-facet skip, sort-then-truncate top-N, value stringification,
aggregate summed-counts + re-sort, aggregate pass-through-by-reference).
