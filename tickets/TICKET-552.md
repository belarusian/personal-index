# TICKET-552: exact-contract docstring for FacetedSearch.search + pinning test

Status: OPEN
Issue: #987

## File
personal_index/search_facets/faceted_search.py

## Symptom
`FacetedSearch.search` (line 97) is a public method whose docstring is a terse
stub: "Search with optional filters and facets." It does not state the exact
contract the code delivers:

- an empty/whitespace `query` skips text filtering entirely (all docs considered);
- a non-empty query keeps only docs sharing >=1 token with the query, sorted by
  match score descending (score = matched query tokens / total query tokens);
- `filters` (when truthy) are AND-ed on top of the text results;
- `total` is the count of docs AFTER text+filter but BEFORE pagination;
- pagination slices `[start:start+page_size]` with `start=(page-1)*page_size`;
- `facets` are built from the FILTERED (post-text, post-filter) docs, not the
  paginated slice, and only when `facet_fields` is truthy (else `{}`).

## Evidence
- Line 107: `"""Search with optional filters and facets."""` (terse stub).
- Lines 108-129: body implements the contract above.
- No pinning test asserts the docstring contract (tests/test_search_facets.py
  TestFacetedSearch covers behavior loosely but not the docstring).

## Minimal additive fix
Reword the `search` docstring to state the exact contract (empty-query skip,
token-overlap text filter + score-descending sort, AND filters, total-before-
pagination, pagination slice, facets-from-filtered-docs). Add a pinning test
class asserting docstring fragments via `doc.lower()` and re-pinning the
non-obvious behaviors (empty query returns all; total counts pre-pagination;
facets built from filtered not paginated docs).
