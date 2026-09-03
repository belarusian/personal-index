# TICKET-302

- Status: RESOLVED
- Module: personal_index/search_facets/faceted_search.py
- Defect class: (b) doc/behavior drift

## Symptom
`FacetedSearch._parse_date_value` docstring promises: "Returns a datetime
object for ISO format strings, or the original value if it's already a number
or not parseable as a date."

The code does NOT honor this. For a string that is not parseable as an ISO
date, the function falls through to `return None` (line ~283), not the
original value.

## Evidence
- Docstring: personal_index/search_facets/faceted_search.py:268-272
- Code: `if isinstance(value, str): try: return datetime.fromisoformat(value)
  except (ValueError, TypeError): pass` then `return None`.
- Runtime: `fs._parse_date_value('not-a-date')` -> `None` (not `'not-a-date'`).
  `fs._parse_date_value(42)` -> `42` (numbers honored).

## Why the code is right and the doc is wrong
All callers treat `None` as the "not a date" sentinel:
- `_matches_range_filter` (line 193-196): `parsed = self._parse_date_value(doc_value); if parsed is None: parsed = doc_value`.
- `_check_between`/`_check_gte`/`_check_lte`/`_check_gt`/`_check_lt`: `if pv is not None: ... else: compare raw`.
Changing the return to the original value would break these `is not None`
branches. The intended contract is: datetime for ISO strings, the value for
numbers, and `None` for anything else. The docstring's "or the original value
if ... not parseable as a date" clause is the drift.

## Minimal additive fix
Correct the docstring to state the actual contract: returns a datetime for
ISO-format strings, the original value for numbers, and `None` for any other
value (including non-parseable strings). Add regression tests pinning all three
branches (ISO string -> datetime, number -> number, unparseable string -> None).

## Issue: #437
