# TICKET-542: content_categorizer._add_matches has no docstring

**Status:** RESOLVED (merged via PR #960, issue #959 closed)
**Issue:** #646

## File
personal_index/content_categorizer.py

## Symptom
`_add_matches` (line 484) has NO docstring at all, while its sibling
`_score_topic` (fixed in cycle 189) and `_match_keywords` carry exact
contracts. The helper's behavior is non-obvious: it dedupes `matches` into
`kw` in place, conditionally appends the `source` label to `src` in place,
and returns the mutated `kw`.

## Evidence
- Line 484-495: `def _add_matches(...)` body with no docstring.
- Sibling `_score_topic` (line 500) has a full 3-tuple contract docstring.

## Minimal additive fix
Add a docstring to `_add_matches` enumerating:
- in-place dedup of `matches` into `kw` (append only if absent)
- in-place append of `source` to `src` ONLY when `matches` is non-empty
  (note: `src` is NOT deduped)
- returns the mutated `kw` list
- `source` default is "text"
Add ONE pinning test calling `_add_matches` directly with a fresh kw/src,
asserting the returned kw fields AND the mutated src (both the non-empty
match path and the empty-match guard path).

## Line-shift guard
tests/test_content_categorizer.py: no line-number refs.
tests/test_exception_handling.py: content_categorizer uses `_method_line_span`
by name (AST-safe); literal ranges are for linker/pipeline/url_history only.
Adding a docstring to `_add_matches` is safe.
