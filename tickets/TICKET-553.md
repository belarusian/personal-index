# TICKET-553: exact-contract docstrings for SimilarityEngine.similarity / find_similar + pinning test

**Status:** CLAIMED 2026-09-07
**Module:** personal_index/content_linker/similarity.py
**Kind:** type-a (public method lacking an exact-contract docstring + pinning test)

## Symptom
`SimilarityEngine.similarity` (line 22) and `SimilarityEngine.find_similar`
(line 44) carry terse one-line docstrings that omit the exact contract the code
actually delivers.

## Evidence
- similarity docstring (line 23): "Compute similarity score between two texts (0.0 to 1.0)."
  The body additionally guarantees: empty/whitespace-only input -> 0.0; a
  symmetric cache key built from (min, max) of the RAW strings; tokenization via
  _tokenize; a no-token guard -> 0.0; and the Jaccard score
  len(intersection) / len(union). None of this is stated.
- find_similar docstring (line 51): "Find items similar to the query text."
  The body additionally guarantees: an item is kept iff
  similarity(query, content) >= threshold; results are sorted by score
  DESCENDING; the list is truncated to the first `limit` entries; and each
  result is a dict with exactly the keys "id" and "score". None of this is
  stated.

## Minimal additive fix
Reword both docstrings to state the exact contract the code delivers, and add a
pinning test class that asserts the docstring fragments (via doc.lower(), to
avoid case/backtick traps) and re-pins the non-obvious behaviors (empty -> 0.0,
symmetric cache key, Jaccard, threshold >=, sort-descending, limit truncation,
result dict shape).
