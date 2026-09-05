# TICKET-397

- STATUS: RESOLVED (merged to main c8e3e59 via PR #633, gh #632 closed)
- File: personal_index/content_summarizer.py
- Function: `_tokenize` (line 42)
- Symptom: class-(b) doc-drift. Docstring `"""Tokenize text into words."""` is a
  generic single-line placeholder that does not enumerate the actual behavior.
- Evidence: line 43 `"""Tokenize text into words."""`; body is
  `return re.findall(r'[a-z0-9]+', text.lower())`.
- Minimal additive fix: reword the docstring to state the exact behavior
  (lowercases the input, returns all maximal runs of lowercase letters and
  digits via `re.findall(r'[a-z0-9]+', ...)`, i.e. splits on any
  non-alphanumeric character and keeps digit runs as separate tokens), and add
  ONE pinning test asserting the corrected claim against the returned list.
- Issue: #632
