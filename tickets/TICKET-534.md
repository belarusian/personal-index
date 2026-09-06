# TICKET-534: ContentCategorizer.get_topic docstring over-promise

- Status: OPEN
- File: personal_index/content_categorizer.py
- Function: ContentCategorizer.get_topic (def line 342, docstring line 343)
- Issue: #942
- Note: renumbered from 533 -> 534 at merge; 533 was claimed by a parallel
  run for DIFFERENT work (ContentRollback.clear, PR #938).

## Symptom
The docstring `"""Get a topic category by name."""` is a single-line generic
placeholder that does not enumerate the actual behavior. The body
`return self._topics.get(name.lower())` performs:
1. lower-cases the input `name` before lookup (case-insensitive),
2. returns the matching `TopicCategory` from the internal `self._topics` dict,
3. returns `None` when no topic with that (case-insensitive) name exists.

## Evidence
- Line 343: `"""Get a topic category by name."""`
- Line 344: `return self._topics.get(name.lower())`

## Minimal additive fix
- Reword the docstring to state the exact behavior: input `name` is
  lower-cased before lookup; returns the matching `TopicCategory` from
  `self._topics`, or `None` when no topic with that (case-insensitive) name
  exists (a caller passing "Tech" matches a stored "tech").
- Add ONE pinning test in tests/test_content_categorizer.py that witnesses:
  add a topic, fetch by the same name (returns the object), fetch by a
  DIFFERENT CASE (still returns it — case-insensitive), and fetch a missing
  name (returns `None`).
