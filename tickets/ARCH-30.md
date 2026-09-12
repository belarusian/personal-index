# ARCH-30: Trending exact-match suggestion score must stay within [0.0, 1.0]

Status: IMPLEMENTED #1283@1b139ca
Component: `personal_index.search_suggestions`
Issue: #1084
Carry-forward: ARCH-2 (#983)

## Symptom
`SearchSuggestions._suggest_from_trending` computes the exact-match score as
`score = min(decayed / max(total_decayed, 1) * 10, 1.0)` and then stores
`Suggestion(score=score * 1.1)`. The `* 1.1` multiplier is applied **after**
the `min(..., 1.0)` clamp, so a single dominant trending entry — whose own
decayed score equals the total, so the base clamps to `1.0` — produces a final
`Suggestion.score` of **`1.1`**. That is outside the `[0.0, 1.0]` range that
`_fuzzy_match_score`'s docstring ("Returns a score between 0.0 and 1.0") and
every other source's weight (history `1.0`, tags `0.9`, keywords `0.8`)
imply. A caller that treats `score` as a normalized confidence (e.g. to
threshold, rank, or display) sees a value > 1.0 only from the trending source.

## Public contract (target)
`SearchSuggestions.suggest(prefix, sources=None, fuzzy=False) ->
list[Suggestion]` must return suggestions whose `score` is always within
`[0.0, 1.0]`, for every source and both `fuzzy=False` and `fuzzy=True`.
Concretely, in `_suggest_from_trending` the trending multiplier must be
applied **before** the clamp (or the clamp must be applied to the final
value), so the stored `Suggestion.score` is `min(base * 1.1, 1.0)` where
`base = decayed / max(total_decayed, 1) * 10`. The relative ordering of
trending suggestions against other sources is preserved (trending still
out-weights an equal base); only the >1.0 overflow is removed.

## Acceptance criteria
1. With a single recorded trending entry that dominates the total,
   `suggest(prefix)` returns a trending `Suggestion` with `score <= 1.0`
   (specifically `min(1.0 * 1.1, 1.0) == 1.0`).
2. With multiple trending entries, no returned `Suggestion.score` exceeds
   `1.0`, and the top trending entry still ranks at or above an equal-base
   non-trending candidate (the `*1.1` boost is retained, just clamped).
3. `fuzzy=True` trending suggestions also stay within `[0.0, 1.0]`.
4. All existing non-trending source scores (history/tags/keywords) are
   unchanged.

## Pinning tests to add
- `test_trending_dominant_entry_score_clamped_to_1_0`:
  `ss = SearchSuggestions(); ss.record_search("python")`
  (single entry → its decayed == total). `sug = ss.suggest("py")`.
  Assert the trending suggestion's `score == 1.0` (not `1.1`) and
  `0.0 <= score <= 1.0`.
- `test_trending_multiple_entries_no_score_exceeds_1_0`:
  record several trending queries, `suggest` on a shared prefix, assert
  every returned `Suggestion.score <= 1.0`.
- `test_trending_fuzzy_score_within_range`:
  `fuzzy=True` path, assert every returned `Suggestion.score <= 1.0`.
- `test_non_trending_scores_unchanged`:
  history/tags/keywords suggestions keep their current scores (regression
  guard that the clamp change did not touch other sources).

## Docs update (same PR)
`docs/search-suggestions.md` "Contract holes" section already documents this
hole (trending-exact-match-score-exceeds-1.0). On implementation, reword that
bullet to state the corrected contract (score clamped to `[0.0, 1.0]` after
the trending multiplier) and keep the page marked **(spec)**.
