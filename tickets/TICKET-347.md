# TICKET-347: content_recommender.recommend_for_keywords docstring over-promises

- File: personal_index/content_recommender.py
- Method: Recommender.recommend_for_keywords (line 164)
- Symptom: docstring says "Recommend content items matching given keywords."
  A blanket "matching" that does not state the exact conditional the body
  performs.
- Evidence (body lines 176-194):
  1. query keywords are lowercased before matching:
     `keyword_set = {kw.lower() for kw in keywords if kw}`
  2. score is the FRACTION of query keywords matched, not a boolean match:
     `score = len(common) / len(keyword_set)`
  3. items are filtered by `min_score` (`if score >= self.min_score`)
     before being sorted and truncated to `top_n`.
  So a query keyword matches case-insensitively, an item is returned only if
  the matched fraction >= min_score, and the score is that fraction. The
  blanket "matching" claimed none of this.
- Minimal additive fix: reword the docstring to the exact conditional
  (lowercased query keywords; score = fraction of query keywords matched;
  filtered by min_score; top_n). Doc-only, no behavior change. Add ONE
  behavior test pinning the corrected claim against the returned object:
  (a) a mixed-case query keyword matches a lowercase item keyword
  (case-insensitive), and (b) the returned score equals the matched fraction.
- Issue: #532
