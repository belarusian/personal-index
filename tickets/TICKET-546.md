# TICKET-546: _score_relevance docstring over-promise (class b)

- File: personal_index/content_scoring.py
- Function: ContentScorer._score_relevance (line ~235)
- Symptom: docstring is the blanket "Score based on keyword relevance." and does
  not enumerate the guard path or the exact formula the body performs.
- Evidence: line 235 `"""Score based on keyword relevance."""` while the body
  (lines 236-238) does: `if total_keywords == 0: return 0.0` then
  `return round(min(1.0, keyword_matches / total_keywords), 4)`.
- Minimal additive fix: reword the docstring to the exact contract (guard path
  total_keywords == 0 -> 0.0; otherwise round(min(1.0, keyword_matches /
  total_keywords), 4)) and add ONE pinning test calling _score_relevance
  directly to pin the guard path (0.0) and the normal ratio path.
- Status: RESOLVED (merged via PR #970, issue #968 closed)
- Issue: #968
