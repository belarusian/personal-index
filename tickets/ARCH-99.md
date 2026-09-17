# ARCH-99: cli_recommend docstring over-promises a seed-content path the command never exposes

- **Status:** CLOSED (validator cycle 263 @ main f989ad2; adversarial deep test tests/deep/test_arch99_adversarial.py 16 passed; Option A docstring reword confirmed, keyword-only input surface pinned, no seed path reachable) #1570@1c210df (impl327, cycle 327)
- **Component:** `personal_index/cli_recommend.py`
- **Kind:** contract hole (docstring over-promise / class-(b) drift)
- **Issue:** #1492

## Symptom

`personal_index/cli_recommend.py:59` — the `recommend` command's docstring
reads:

> Get content recommendations based on a query **or seed content**.

But the command exposes only a single `query` argument
(`@click.argument("query", required=False)`, line 43) and its body ALWAYS
calls `Recommender.recommend_for_keywords(keywords, top_n, ...)` (lines 80
and 87). There is no `--seed` option, no second argument, and no code path
that constructs a `ContentItem` seed and calls the engine's seed-based
`Recommender.recommend(seed, ...)` (`personal_index/content_recommender.py:137`).

So the "or seed content" clause advertises a capability the CLI cannot
reach. The engine DOES have a seed-based method (`recommend(seed, ...)`,
which honors all three weights and excludes the seed by URL), but this
command never wires it up. A user reading the docstring (or `--help`)
believes they can get seed-based recommendations; they cannot.

This is a class-(b) docstring over-promise: the code is internally
consistent (keyword-only), the docstring over-states it. The existing
validator deep test already pins the CURRENT keyword-only behavior, so the
minimal fix is doc-only and that deep test is the witness.

## Evidence (file:line)

- `personal_index/cli_recommend.py:59` — docstring "based on a query **or
  seed content**".
- `personal_index/cli_recommend.py:43` — the ONLY argument is `query`
  (`required=False`); no seed argument or `--seed` option.
- `personal_index/cli_recommend.py:80` — explicit-weight branch calls
  `recommender.recommend_for_keywords(keywords, top_n, ...)`.
- `personal_index/cli_recommend.py:87` — default branch calls
  `recommender.recommend_for_keywords(keywords, top_n)`.
- `personal_index/cli_recommend.py:66` — `keywords = query.split() if query
  else []`; the only input to scoring is the split query.
- `personal_index/content_recommender.py:137` — `def recommend(self, seed,
  top_n=5, keyword_weight=0.6, tag_weight=0.3, score_weight=0.1)` exists in
  the engine but is never called from `cli_recommend.py`.
- `grep -n 'recommend(' personal_index/cli_recommend.py` returns only the
  `recommend_for_keywords` calls (lines 80, 87) — no bare `recommend(seed)`
  call.
- **Witness (validator-owned, already pins current behavior):**
  `tests/deep/test_cli_recommend_adversarial.py:13-20` — the module docstring
  states the command "calls `Recommender.recommend_for_keywords(keywords,
  top_n)`" and that the seed-based `recommend` path "DOES honor weights" but
  is a separate engine method; the file's CLI tests (lines 62-245) exercise
  only the keyword path end-to-end. This is the witness that the corrected
  docstring (keyword-only) matches reality.

## Public contract (what the fix must preserve / establish)

The reachable `personal-index recommend` command must keep its current
keyword-based behavior. The fix is a DECISION between two options; either is
acceptable, but `docs/cli_recommend.md` and this ticket must state which was
chosen:

- **Option A (reword the docstring — doc-only, minimal):** change line 59 to
  state the exact contract the body performs, e.g. "Get content
  recommendations by matching a query's keywords against indexed content."
  Remove the "or seed content" clause. No code change; the existing deep test
  is the witness that the corrected docstring matches the keyword-only
  behavior.
- **Option B (wire the seed path):** add a `--seed-url` (or `--seed`) option
  that, when supplied, loads that page as a `ContentItem` seed and calls
  `Recommender.recommend(seed, top_n, keyword_weight, tag_weight,
  score_weight)`; when absent, fall back to the current keyword path. The
  docstring's "or seed content" then becomes true.

Guard inputs the contract must pin (whichever option):
- No `query` (empty) → `keywords == []` → `recommend_for_keywords([], top_n)`
  → `No recommendations found.` (guard path, already pinned by deep test
  `test_no_query_empty_keywords`).
- `query` present but no matches → `No recommendations found.` (deep test
  `test_query_no_matches`).
- Empty index (`item_count == 0`) → `No indexed content found. Run
  'personal-index pipeline' first.` (deep test `test_empty_index_no_file`).
- (Option B only) `--seed-url` pointing at an indexed page → seed-based
  `recommend` output, seed excluded by URL; `--seed-url` for a URL not in the
  index → documented behavior (no seed found → fall back to keyword path or
  `No recommendations found.`, whichever is chosen).

## Acceptance criteria

1. The `recommend` command's docstring (line 59) matches the actual reachable
   behavior: either it no longer claims a seed-content path (Option A) or a
   seed path is genuinely reachable (Option B). No advertised-but-unreachable
   capability remains.
2. `docs/cli_recommend.md` states which option (A or B) was implemented and
   the resulting reachable input surface; the "Known contract hole" section
   is updated to reflect the resolution.
3. A pinning test pins the CORRECTED claim against the returned output (not
   just the docstring wording): for Option A, the existing deep test
   `tests/deep/test_cli_recommend_adversarial.py` (keyword-path end-to-end,
   lines 62-245) is the witness — no new test required, but the implementer
   must confirm it stays green after the docstring reword (line-shift check:
   the reword must not break any line-range-pinned test in `tests/`). For
   Option B, add a `CliRunner` test that runs `["recommend", "--seed-url",
   <url>, ...]` against `cli.main` and pins the seed-based output (seed
   excluded, weights honored) plus the guard path for an unknown seed URL.
4. `grep -n 'recommend(' personal_index/cli_recommend.py` is consistent with
   the chosen option: Option A → only `recommend_for_keywords` calls;
   Option B → a `recommend(seed)` call reachable from a CLI option.

## Pinning tests to add (IMPLEMENTER owns tests/**)

- **Option A (preferred, minimal):** no new test. The witness is the existing
  `tests/deep/test_cli_recommend_adversarial.py` keyword-path suite. The
  implementer re-runs it after the docstring reword and confirms green
  (line-shift guard: grep the WHOLE `tests/` tree for literal line-number
  pins before committing the reword).
- **Option B:** a new `CliRunner` test in `tests/test_cli_recommend.py` (or
  the deep file) that drives `--seed-url` end-to-end and pins seed-exclusion
  + weight-honoring + the unknown-seed guard path.

## Proposed fix

Option A is preferred: the command was clearly built as a keyword-query tool
(the `query` argument, `query.split()`, and both branches calling
`recommend_for_keywords`), and the "or seed content" clause is a leftover
over-promise. Reword line 59 to the exact keyword contract. Option B is the
larger diff (new option + seed-loading + a new scoring branch) and is only
worth it if seed-based recommendations are a real product requirement.

## Self-review checklist (architect)

- [x] Component named (`personal_index/cli_recommend.py`).
- [x] Public contract stated (reachable input surface, guard inputs,
      empty-result behavior, the two resolution options).
- [x] Evidence is file:line, verified against current code on this branch.
- [x] Witness identified (validator deep test already pins current
      keyword-only behavior → Option A is doc-only).
- [x] Acceptance criteria are checkable without conversation.
- [x] Pinning tests specified (Option A: existing deep test is the witness;
      Option B: new seed-path end-to-end test).
- [x] Docs page `docs/cli_recommend.md` shipped in the SAME PR and states the
      hole + the option to choose.
- [x] No code/test written by architect (design-only; implementer owns the
      fix + tests).
- CLOSED (architect, cycle 311): contract VERIFIED by the validator (PR #1570); docs reconciled; closing the VERIFIED pile.
