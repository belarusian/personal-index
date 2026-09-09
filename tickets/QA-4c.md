Status: CLAIMED 2026-09-09
Kind: QA
Issue: #1047 (split of QA-4 class sweep, part C)

# QA-4c: negative-slice guard — sites 9-13 (content_linker, search_index, content_search, content_scoring, text_utils)
| # | module | function | line | idiom |
|---|--------|----------|------|-------|
| 9 | content_linker/linker.py | ContentLinker.find_related(limit) | ~124 | results[:limit] |
| 10 | search_index.py | SearchIndex.search(limit) | ~148 | results[:limit] |
| 11 | content_search.py | SearchIndex.get_suggestions(limit) | ~483 | suggestions[:limit] |
| 12 | content_scoring.py | ContentScorer.rank(limit) | ~458 | scored[:limit] |
| 13 | text_utils.py | extract_keywords(top_n) | ~152 | result[:top_n] |
Acceptance: each returns [] for N<=0, unchanged for N>0; docstring states guard; add passing regression test per site.
