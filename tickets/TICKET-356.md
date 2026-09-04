# TICKET-356: TfidfScorer.rank_documents docstring over-promises "all documents"

Status: RESOLVED
Issue: #550
Module: personal_index/tfidf.py
Symptom: rank_documents docstring says "Rank all documents by relevance to query"
  but the body filters with `if score > 0` (line 76), excluding documents with
  zero TF-IDF score (no term overlap with query).
Evidence: line 76: `if score > 0:` — zero-score docs are never appended to scores list.
Fix: Reword docstring to "Rank documents with positive TF-IDF score by relevance
  to query." Add one behavior test pinning the corrected claim: a corpus with one
  matching + one non-matching doc returns only the matching doc.
