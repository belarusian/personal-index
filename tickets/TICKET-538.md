# TICKET-538: ContentCategorizer.get_topics docstring omits sorted behavior

Status: OPEN
- File: personal_index/content_categorizer.py
- Function: ContentCategorizer.get_topics (def line 338, docstring line 339)
- Issue: #951

## Symptom
The docstring `"""Get list of all available topic names."""` is a single-line
generic placeholder that does not enumerate the actual behavior. The body
`return sorted(self._topics.keys())` performs:
1. collects every topic name currently stored in the internal `self._topics`
   dict,
2. returns them sorted in ascending (lexicographic) order,
3. returns an empty list when no topics have been added.

## Evidence
- Line 339: `"""Get list of all available topic names."""`
- Line 340: `return sorted(self._topics.keys())`

## Minimal additive fix
- Reword the docstring to state the exact behavior: returns a list of every
  topic name currently stored in `self._topics`, sorted in ascending
  (lexicographic) order; returns an empty list when no topics have been added.
- Add ONE pinning test in tests/test_content_categorizer.py that witnesses:
  add two topics whose names are out of lexicographic order ("zeta" then
  "alpha") and assert the returned list is sorted ascending (not insertion
  order); also assert an empty topic store returns [].
