Status: IMPLEMENTED PR #1115@359c502 (cycle 198: negslice guard sites 5-8 done)
Kind: QA
Issue: #1047 (split of QA-4 class sweep, part B)

# QA-4b: negative-slice guard — sites 5-8 (content_recommender.recommend_for_keywords, search_suggestions x2, content_monitor)
| # | module | function | line | idiom |
|---|--------|----------|------|-------|
| 5 | content_recommender.py | Recommender.recommend_for_keywords(top_n) | ~229 | candidates[:top_n] |
| 6 | search_suggestions.py | SearchSuggestions.get_trending(n) | ~151 | scored[:n] |
| 7 | search_suggestions.py | SearchSuggestions.get_related_queries(n) | ~358 | sorted_related[:n] |
| 8 | content_monitor/monitor.py | ContentMonitor.get_disk_usage(top_n) | ~74 | all_files[:top_n] |
Acceptance: each returns [] for N<=0, unchanged for N>0; docstring states guard; add passing regression test per site.
