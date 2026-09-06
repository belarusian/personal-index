# TICKET-532: content_summarizer._split_sentences docstring over-promise

- File: personal_index/content_summarizer.py
- Function: `_split_sentences` (line 27, docstring line 28)
- Symptom: class-(b) doc-drift. Docstring reads
  `"""Split text into sentences, handling common abbreviations."""` but the body
  does NOT handle common abbreviations at all. It (1) normalizes whitespace via
  `re.sub(r'\s+', ' ', text).strip()`, (2) returns `[]` for empty/whitespace-only
  text, (3) splits on `re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)` (sentence-ending
  punctuation followed by whitespace and an uppercase letter), and (4) strips and
  drops empty fragments. No abbreviation table / lookahead is present.
- Evidence: sed -n '27,41p' personal_index/content_summarizer.py
- Minimal additive fix: reword the docstring to state the exact behavior
  (whitespace normalization, empty-text guard, the split regex, empty-fragment
  filter, returned list). Add ONE pinning test in tests/test_content_summarizer.py
  that witnesses the split behavior AND the empty-text guard path against the
  returned list.
- Status: RESOLVED (merged via PR #940, issue #939 closed)
- Issue: #939
