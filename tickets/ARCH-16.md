Status: OPEN
Kind: ARCH
Author: architect (cycle 178)
Issue: #1044

# ARCH-16: `Recommender.recommend_for_keywords` docstring over-promises "matching is case-insensitive"

## Component
`personal_index.content_recommender.Recommender.recommend_for_keywords`
(content_recommender.py).

## Symptom
The docstring states: "Query keywords are lowercased before matching, so
matching is case-insensitive." That is only half true. The *query* keywords are
lowercased (`keyword_set = {kw.lower() for kw in keywords if kw}`), but an
item's **explicit** `keywords` are matched case-sensitively: `all_keywords`
adds `set(self.keywords)` as-is (no lowercasing); only the content/title-derived
keywords are lowercased by `_extract_keywords`. So a query keyword `"Python"`
(lowercased to `"python"`) matches an item whose explicit keyword is the
lowercase `"python"`, but does NOT match an item whose explicit keyword is the
mixed-case `"Python"`.

The existing test `test_recommend_for_keywords_case_insensitive_and_fraction_score`
pins the query-side lowercasing (query `"Python"` matches item keyword
`"python"`), but it does NOT pin the explicit-keyword case, so the over-promise
is un-witnessed.

## Public contract (the code is the truth)
`recommend_for_keywords(keywords, top_n=5) -> list[Recommendation]`:
- **Query side:** query keywords are lowercased and empty strings dropped.
- **Item side:** an item's explicit `keywords` are matched **case-sensitively**
  (added to `all_keywords` as-is); only content/title-derived keywords are
  lowercased.
- **Behavior:** each item's score is `len(common) / len(keyword_set)` (the
  matched fraction); items below `min_score` are dropped; survivors sorted by
  score (descending) and truncated to `top_n`.

## Acceptance criteria
1. The docstring states the EXACT conditional: query keywords are lowercased;
   an item's explicit `keywords` are matched case-sensitively (only
   content/title-derived keywords are lowercased).
2. A pinning test witnesses the corrected claim against the returned object:
   a query keyword that differs in case from an item's explicit keyword does
   NOT match (returns `[]`).

## Pinning tests to add (tests/test_content_recommender.py)
- `test_recommend_for_keywords_explicit_keywords_case_sensitive`:
  - Build a pool with one item whose explicit `keywords=["Python"]` (mixed
    case) and empty `content`/`title` (so `all_keywords == {"Python"}`).
  - Assert `recommender.recommend_for_keywords(["python"], top_n=5) == []` —
    the query is lowercased to `"python"`, which does NOT match the explicit
    `"Python"` (case-sensitive item side).
  - Include the guard-path input (empty query `[]` -> `[]`) alongside, so one
    test pins both the case-sensitivity claim and the empty-query guard.

## Docs update (same PR)
`docs/content-recommender.md` — the `recommend_for_keywords` entry already lists
this as a contract hole (ARCH-16); on fix, reword the docstring to the exact
conditional and mark the hole Resolved (ARCH-16, cycle N).
