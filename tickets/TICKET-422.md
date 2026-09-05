# TICKET-422: content_recommender.Recommender.recommend blanket docstring

- File: personal_index/content_recommender.py
- Function: Recommender.recommend (line 136)
- Symptom (class-b doc-drift): docstring is the blanket one-liner
  "Generate recommendations based on a seed content item." It does not
  enumerate the empty-pool guard, the self-exclusion, the two Jaccard
  sub-scores, the weighted combination, the min_score drop, the reason
  construction, or the returned Recommendation fields.
- Evidence: line 144 `"""Generate recommendations based on a seed content item."""`
  vs body lines 145-157 (empty-pool `return []`, `item.url == seed.url` skip,
  `_keyword_overlap_score` / `_tag_similarity_score`, `_build_recommendation`,
  `candidates.sort(...reverse=True)`, `candidates[:top_n]`).
- Minimal additive fix: reword the docstring to state the EXACT behavior
  (empty-pool guard returns []; seed excluded by url; keyword-overlap and
  tag-similarity Jaccard sub-scores; weighted combination
  kw*kw_w + tag*tag_w + norm*sc_w with norm=min(score/10,1.0) if score>0 else 0.0;
  combined < min_score dropped; reason = "keywords: top5" / "tags: all" /
  "score-based"; sorted by score desc, truncated to top_n; returned
  Recommendation fields url/title/score/reason/matching_keywords/matching_tags).
  Add ONE pinning test asserting the returned Recommendation object fields for a
  normal case AND the empty-pool guard path (recommend on empty pool == []).
- Status: OPEN
- Issue: #682
