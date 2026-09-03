# TICKET-327: content_recommender module docstring promises "interest matching" that no code implements

- File: personal_index/content_recommender.py
- Status: RESOLVED
- Class: (b) doc/behavior drift

## Symptom
The module docstring (line 4) promises recommendations are based on "keyword
overlap, tag similarity, and interest matching scores." No interest matching
exists anywhere in the module: the word "interest" appears only in the module
docstring. The class docstring (lines 75-77) correctly says recommendations are
based on "keyword overlap, tag similarity, and existing scores." `recommend()`
computes only `_keyword_overlap_score`, `_tag_similarity_score`, and the item's
existing `score` (via `score_weight` / `norm = item.score / 10.0`). `ContentItem`
has no interest field and there is no interest-matching function.

## Evidence
- `grep -n interest personal_index/content_recommender.py` -> only line 4 (module docstring).
- `recommend()` uses keyword overlap + tag similarity + existing score only.
- `ContentItem` fields: url, title, content, keywords, tags, score (no interest).
- Class docstring already states "existing scores" (the truth).

## Minimal additive fix
Correct the module docstring to describe the signals actually implemented
(keyword overlap, tag similarity, and existing scores), removing the
unimplemented "interest matching" claim. Add ONE regression test asserting the
module docstring does not promise an "interest" matching capability.

## Issue: #492
