Status: CLAIMED 2026-09-09
Kind: QA
Issue: #1047 (split of QA-4 class sweep, part A)

# QA-4a: negative-slice guard — sites 1-4 (progress, content_annotations, content_collections, content_recommender.recommend)

Part A of the QA-4 negative-slice "top N / recent N" class sweep (Issue #1047).
Fix these 4 sites so a negative bound returns [] (clamp to max(0,N) before slicing):
| # | module | function | line | idiom |
|---|--------|----------|------|-------|
| 1 | progress.py | ProgressStore.list_completed(limit) | ~235 | completed[:limit] |
| 2 | content_annotations.py | AnnotationManager.get_recent(limit) | ~193 | all_ann[:limit] |
| 3 | content_collections.py | CollectionManager.get_recent(limit) | ~326 | all_c[:limit] |
| 4 | content_recommender.py | Recommender.recommend(top_n) | ~185 | candidates[:top_n] |

Acceptance: each function returns [] for N<=0 and unchanged for N>0; docstring states the guard.
Flip the pinning xfail-strict test tests/deep/test_progress_adversarial.py::test_list_completed_negative_limit_returns_empty (site 1) so it PASSES.
Add a passing regression test per site (negative bound -> []).
