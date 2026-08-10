# TICKET-3: Dead code — personal_index/similarity.py is unused

## Title
`personal_index/similarity.py` is not imported by any production code

## Evidence
- `personal_index/similarity.py` defines `SimilarityEngine` and `SimilarityResult`
- The only import of this module is in `tests/test_similarity.py:4`
- No production code imports it:
