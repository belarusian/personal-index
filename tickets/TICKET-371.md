# TICKET-371

- File: personal_index/formatter.py
- Function: highlight(text, terms)
- Class: (a) behavioral
- Symptom: highlight() applies terms via sequential str.replace(). When one
  term is a substring of another, the shorter term is matched inside the
  already-inserted **longer** marker, corrupting the output.
- Evidence:
    >>> highlight('cat catalog', ['cat', 'catalog'])
    '**cat** **cat**alog'   # expected 'cat **catalog**'
    >>> highlight('pythonic code', ['python', 'pythonic'])
    '**python**ic code'     # expected '**pythonic** code'
  formatter.py:172-179 (the `for term in terms: result = result.replace(...)` loop).
- Note: sorting terms by length descending alone is NOT sufficient — after
  replacing 'catalog' -> '**catalog**', the 'cat' inside the marker is still
  matched by a later 'cat' pass. A single-pass regex with alternation ordered
  longest-first is required so each source position is matched exactly once.
- Minimal additive fix: replace the sequential replace loop with a single
  re.sub over an alternation of re.escape(term) sorted by len descending,
  wrapping each match in ** markers. Preserve the empty-terms and empty-term
  guards.
- Test: add tests/test_formatter.py::TestHighlight::test_substring_terms that
  asserts highlight('cat catalog', ['cat','catalog']) == 'cat **catalog**'
  (fails pre-fix, passes post-fix).
- Status: OPEN
- Issue: #580
