# TICKET-543: Add exact-contract docstrings to Facet.add_value / Facet.sort_values + pinning test

Status: OPEN
Module: personal_index/search_facets/facet.py
Methods: Facet.add_value, Facet.sort_values

## Symptom
Both public methods carry one-line stub docstrings that omit the exact contract the code delivers.

- add_value docstring: "Add or update a facet value."
  Omitted contract the code actually delivers:
  (1) if a value with the same name already exists, its count is INCREMENTED by count (existing.count += count), not replaced;
  (2) otherwise a new FacetValue(name, count) is appended to self.values;
  (3) count defaults to 1 when omitted;
  (4) returns None (mutates in place).

- sort_values docstring: "Sort values by count descending."
  Omitted contract the code actually delivers:
  (1) sorts self.values IN PLACE (mutates the list, does not return a new list);
  (2) key is count, reverse=True (highest count first);
  (3) Python sort is STABLE, so values with equal count preserve their prior (insertion) relative order;
  (4) returns None.

## Evidence (verified live on main)
- Facet().add_value('a', count=5); add_value('a', count=3) -> values[0].count == 8 (increment, not replace)
- Facet().add_value('x') -> values[0].count == 1 (default count)
- add three values all count=5, sort_values() -> order ['a','b','c'] (stable, insertion order preserved on ties)
- sort_values() returns None; add_value() returns None

Existing tests (tests/test_search_facets.py) pin: add_value creates a value (count=5), multiple values, sort_values puts highest count first. They do NOT pin the increment behavior, the default count=1, the stable-sort tie ordering, or the docstring contract phrases.

No reword commit exists in git history for facet.py (git log shows only the original "feat: add search_facets module" commit) -- a fresh type-a case, not a doc-drift recovery.

## Minimal additive fix
Reword the add_value and sort_values docstrings to state the exact contract above. Add a pinning test class (TestFacetDocstring543) asserting the key contract phrases appear in the docstrings AND re-pinning the non-obvious behaviors (increment on same-name, default count=1, stable tie ordering, both return None).

## Issue: #961
