# TICKET-372: highlight_text() sequential sub re-matches shorter terms inside longer-term markers

- **File:** personal_index/text_utils.py
- **Function:** highlight_text (line 224)
- **Symptom:** Sequential `for term: pattern.sub(...)` loop re-matches shorter
  terms inside HTML markers already inserted for longer terms. E.g.
  `highlight_text('catalog cat', ['catalog', 'cat'])` produces
  `<mark><mark>cat</mark>alog</mark> <mark>cat</mark>` instead of
  `<mark>catalog</mark> <mark>cat</mark>`.
- **Evidence:** line 237-241: `for term in terms: ... result = pattern.sub(f"<{tag}>{term}</{tag}>", result)`
  — each iteration operates on the already-modified `result`, so a later
  shorter term matches inside the marker text a longer term just inserted.
  Same defect class as TICKET-371 (formatter.highlight), fixed there with a
  single-pass regex alternation (longest-first).
- **Minimal additive fix:** Replace the sequential loop with a single-pass
  `re.sub` over an alternation of `re.escape(term)` sorted longest-first,
  so each source position is matched at most once.
- **Test:** Add `test_substring_terms` to tests/test_text_utils.py
  (TestHighlightText) that asserts the corrected output.
- **Status:** OPEN
Issue: #582
