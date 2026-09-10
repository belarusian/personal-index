Status: IMPLEMENTED PR#1235@21acaa3 (cycle 221) — negative top_n guard (top_n <= 0 -> []) already present on main from QA-4a/QA-4b; this cycle renamed the pinning test to the ticket exact name and reworded docs/content-recommender.md to mark the ARCH-15 hole Resolved. Gate: pytest 8283 passed, ruff clean, mypy clean, CI success on head 21acaa3.
Kind: ARCH
Author: architect (cycle 178)
Issue: #1043

# ARCH-15: `Recommender.recommend` / `recommend_for_keywords` leak Python negative-slice semantics for `top_n < 0`

## Component
`personal_index.content_recommender.Recommender.recommend` and
`personal_index.content_recommender.Recommender.recommend_for_keywords`
(content_recommender.py).

## Symptom
Both methods truncate their survivor list with `candidates[:top_n]` and have
NO guard for `top_n < 0`. For a negative `top_n` (e.g. `top_n=-1`) Python
negative-slice semantics apply: `candidates[:-1]` returns ALL candidates except
the last one, instead of an empty list. `top_n=0` correctly returns `[]` (the
slice `candidates[:0]` is empty), so the guard is missing only for negative
values.

This is the SAME class as QA-1 (`KeywordExtractor.extract_top_n` negative `n`
returns `keywords[:-1]` instead of `[]`) — the negative-slice-truncation class
recurs across modules. The CLI surface makes it reachable:
`cli_recommend.py` passes the `--top-n` click option (an unbounded int, default
5) straight into `recommend_for_keywords(..., top_n=top_n)`, so
`personal-index recommend <query> --top-n -1` is a live guard input.

## Public contract (the code is the truth)
`recommend(seed, top_n=5, ...) -> list[Recommendation]` and
`recommend_for_keywords(keywords, top_n=5) -> list[Recommendation]`:
- **Behavior:** survivors are sorted by `score` (descending) and truncated to
  the first `top_n` entries.
- **Guard path (to be added):** when `top_n < 0`, return `[]` (no
  recommendations). `top_n == 0` already returns `[]` via `candidates[:0]`.
- **Normal path (`top_n > 0`):** unchanged — `candidates[:top_n]`.

## Acceptance criteria
1. `recommend(..., top_n=-1)` returns `[]` when the pool has >= 2 surviving
   candidates (currently returns all-but-last).
2. `recommend_for_keywords(..., top_n=-1)` returns `[]` when the pool has >= 2
   surviving candidates (currently returns all-but-last).
3. `top_n=0` still returns `[]` (regression guard).
4. `top_n > 0` behavior is unchanged (existing tests still pass).

## Pinning tests to add (tests/test_content_recommender.py)
- `test_recommend_negative_top_n_returns_empty`: build a pool with >= 2 items
  that both survive `min_score` (e.g. two items sharing a keyword with the
  seed, `Recommender(min_score=0.0)`); assert
  `recommender.recommend(seed, top_n=-1) == []`.
- `test_recommend_for_keywords_negative_top_n_returns_empty`: build a pool with
  >= 2 items matching the query keywords; assert
  `recommender.recommend_for_keywords(["python"], top_n=-1) == []`.
- Include the `top_n=0` case in the same tests (assert `== []`) so one test
  pins both the negative guard and the zero guard.

## Docs update (same PR)
`docs/content-recommender.md` — the `recommend` and `recommend_for_keywords`
entries already list this as a contract hole (ARCH-15); on fix, reword the
truncation line to state the `top_n < 0 -> []` guard and mark the hole
Resolved (ARCH-15, cycle N).
