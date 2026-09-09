Status: CLOSED (validator cycle 158: re-ran repro - rank_documents(-1)->[], get_top_terms(-1)->[], CLI search --limit -1 -> No results; deep tests TestNegativeSliceLeak + TestCliSearchEndToEnd pass)
Kind: QA
Issue: #1037
Deep test: tests/deep/test_tfidf_adversarial.py (test_rank_documents_negative_limit, test_get_top_terms_negative_n, test_cli_search_negative_limit - all xfail-strict)

# QA-2: negative-slice semantics leak into the "top N" / "limit" contract (tfidf + CLI search)

## Symptom
Three "top N" / "limit" APIs leak Python negative-slice semantics: a negative
`n`/`limit` returns `list[:-1]` (all-but-last) instead of an empty list, while
the `n=0` / `limit=0` guard correctly returns `[]`. Out-of-range (negative) N
must yield an empty list, matching the zero guard.

Affected sites (same defect class as QA-1, which is `extract_top_n`):
1. `personal_index/tfidf.py` `TfidfScorer.rank_documents(query, limit=-1)`
   -> `scores[:limit]` -> `scores[:-1]`
2. `personal_index/tfidf.py` `TfidfScorer.get_top_terms(doc_id, n=-1)`
   -> `sorted(...)[:n]` -> `[:-1]`
3. `personal_index/index.py` `SearchIndex.search(query, limit=-1)`
   -> `results[:limit]` -> `[:-1]` (reachable via the installed CLI
   `personal-index search --limit -1`)

## Exact repro
    python3 -c "
    from personal_index.tfidf import TfidfScorer
    s = TfidfScorer()
    s.add_document('alpha beta gamma')
    s.add_document('beta delta epsilon')
    s.add_document('gamma zeta eta')
    print(s.rank_documents('beta', -1))
    print(s.rank_documents('beta',  0))
    print(s.get_top_terms(0, -1))
    print(s.get_top_terms(0,  0))
    "

## Observed output
    [(0, 0.42922735748392693)]
    []
    [('alpha', 0.5643823935199818), ('beta', 0.42922735748392693)]
    []
`rank_documents('beta', -1)` returns 1 result (all-but-last of the 2 scored
docs); `get_top_terms(0, -1)` returns 2 terms (all-but-last of the 3). Both
should be `[]` to match the `0` guard.

CLI repro (installed CLI):
    personal-index search beta --limit -1 --data-dir <dd>   # returns 1 of 2
    personal-index search beta --limit  0 --data-dir <dd>   # returns 0 (correct)

## Expected per docs
- `rank_documents` docstring: "Rank documents ... by relevance to query" with a
  `limit` parameter (default 10). A negative limit is out-of-range and must
  yield an empty list, consistent with `limit=0` -> `[]`.
- `get_top_terms` docstring: "Get top N terms by TF-IDF score for a document."
  A negative N is out-of-range and must yield an empty list, consistent with
  `n=0` -> `[]`.
- `SearchIndex.search` docstring: "Search the index." with a `limit` parameter.
  A negative limit is out-of-range and must yield no results, consistent with
  `limit=0` -> `[]`.

## Deep test
tests/deep/test_tfidf_adversarial.py
  - test_rank_documents_negative_limit   (xfail-strict)
  - test_get_top_terms_negative_n        (xfail-strict)
  - test_cli_search_negative_limit       (xfail-strict)
