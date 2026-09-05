# TICKET-414

- Module: personal_index/content_search.py
- Function: SearchIndex.search (line 284, docstring line 293)
- Status: OPEN
- Class: (b) doc-drift (docstring under-promises / does not enumerate behavior)

## Symptom
Docstring is a single blanket line: "Search the index and return ranked results."
It does not enumerate:
  - the GUARD path: when the query tokenizes to no tokens (empty query, or a
    query of only stop-words / punctuation / single characters) it returns
    exactly {"results": [], "total": 0, "query": query} without touching the index.
  - the RETURN dict fields for the normal path: results, total, query.
  - the "total" vs page distinction: total = len(ranked) = the count of ALL
    ranked candidates BEFORE the offset:offset+limit page slice (so total can
    exceed len(results)).
  - the ENTRY structure (from _build_entry): each entry is a dict with "item"
    (the stored item with its "content" key removed) and "score" (rounded to 4
    decimals); when highlight=True each entry also carries "snippets" (a list
    of Snippet.to_dict() dicts), and the key is absent when highlight=False.
  - the ranking options ("tf" default = summed term frequency, "tfidf", "bm25")
    and that filters narrow candidates before ranking.

## Evidence
personal_index/content_search.py:284-311 (search body), 273-283 (_build_entry)

## Minimal additive fix
Reword the docstring to state the exact guard path and enumerate the returned
dict fields + entry structure + total-vs-page semantics. Add ONE pinning test
asserting the returned object fields for BOTH the normal case (query echoed,
total == all ranked pre-page, page sliced to limit, entry keys exactly
{item, score} with content stripped and score rounded to 4, snippets key absent
when highlight=False and present with 5 fields when highlight=True) and the
guard/empty case (returns exactly {"results": [], "total": 0, "query": ...}).

## Issue: #664
