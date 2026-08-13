# TICKET-236: faceted_search.py — Add test coverage for range filters, nested filters, and list filters

**File:** `personal_index/search_facets/faceted_search.py`  
**Test file:** `tests/test_search_facets.py`  
**Severity:** S1 — Missing test coverage for core functionality  
**Cycle:** 12

## Evidence

`test_search_facets.py` has 10 `TestFacetedSearch` tests covering basic operations:
- `add_document`, `remove_document`, `clear`, `get_documents`, `get_available_facets`
- Basic text search, basic exact-match filters, pagination, `to_dict`

**Untested code paths** (all in `FacetedSearch` class):

| Method | Lines | Coverage Gap |
|--------|-------|-------------|
| `_matches_range_filter` | 163–181 | `$between`, `$gte`, `$lte`, `$gt`, `$lt`, `$in`, `$not` operators — zero tests |
| `_check_between` | 183–192 | Date range and numeric range filtering |
| `_check_gte` / `_check_lte` | 194–204 | Greater/less-than-or-equal filtering |
| `_check_gt` / `_check_lt` | 206–216 | Strict greater/less-than filtering |
| `_check_in` | 218–223 | Set membership filtering |
| `_check_not` | 225–228 | Exclusion filtering |
| `_get_nested_value` | 143–152 | Dot-notation nested field access (e.g., `metadata.author`) |
| `_matches_all_filters` list branch | 157–161 | List intersection filter (`filters={"tags": ["python"]}`) |
| `_extract_text` | 107–113 | Text extraction from list fields |
| `SearchResults.__getitem__` | 30–32 | Dict-style access |
| `SearchResults.__contains__` | 34–38 | `in` operator support |
| `SearchResults.keys()` | 40–42 | Key enumeration |
| `_parse_date_value` | 230–243 | ISO date string parsing |

## Impact

The range filter system (lines 163–228) is the most complex logic in the module — 7 filter operators with date parsing — and has **zero test coverage**. A regression in any of these operators would go undetected.

## Suggestion

Add a `TestFacetedSearchFilters` class with these tests:

1. **Range filters:**
   - `test_filter_gte` — `filters={"score": {"$gte": 5}}`
   - `test_filter_lte` — `filters={"score": {"$lte": 10}}`
   - `test_filter_gt` — `filters={"score": {"$gt": 5}}`
   - `test_filter_lt` — `filters={"score": {"$lt": 10}}`
   - `test_filter_between` — `filters={"score": {"$between": [5, 10]}}`
   - `test_filter_in` — `filters={"category": {"$in": ["tech", "science"]}}`
   - `test_filter_not` — `filters={"category": {"$not": "cooking"}}`

2. **Date range filters:**
   - `test_filter_date_gte` — ISO date strings with `$gte`
   - `test_filter_date_between` — ISO date strings with `$between`

3. **Nested field filters:**
   - `test_filter_nested_dot_notation` — `filters={"metadata.author": "alice"}`

4. **List intersection filters:**
   - `test_filter_list_intersection` — `filters={"tags": ["python", "web"]}` matches doc with `tags=["python", "api"]`

5. **SearchResults dict-style access:**
   - `test_search_results_getitem` — `results["results"]`
   - `test_search_results_contains` — `"results" in results`
   - `test_search_results_keys` — `results.keys()`

6. **Combined filters:**
   - `test_combined_range_and_exact` — range filter + exact match together
