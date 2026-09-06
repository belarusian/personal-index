# TICKET-469: TfidfScorer.score_query docstring over-promises "TF-IDF dot product"

- File: personal_index/tfidf.py
- Function: TfidfScorer.score_query (line 62)
- Symptom: docstring says "Score a document against a query using TF-IDF dot
  product." but the body applies TF-IDF only to the DOCUMENT side
  (self.compute_tfidf(doc_id)); the QUERY side uses raw normalized term
  frequency (query_tf = count / query_total, no IDF weighting). So the score is
  a dot product of the query TF vector and the document TF-IDF vector, not a
  TF-IDF dot product on both sides.
- Evidence: tfidf.py lines 62-77. `query_tf = count / query_total` (line 74)
  has no IDF factor; only `doc_tfidf[term]` (line 75) is TF-IDF.
- Minimal additive fix: reword the docstring to state the exact computation
  (dot product of query normalized-TF vector with document TF-IDF vector) and
  the guard conditions (returns 0.0 when the query yields no tokens after
  stopword removal, or the document is not in the corpus). Add ONE behavior
  test pinning the corrected claim: normal case (score > 0) + guard path
  (all-stopword query -> 0.0, unknown doc -> 0.0).
- Issue: #783
