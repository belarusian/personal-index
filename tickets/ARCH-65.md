# ARCH-65 — negative-slice "top N / limit" guard: extend the class rule to the OFFSET form (`list[offset:offset+N]`) and register the two new per-site instances (QA-15 #1186, QA-16 #1191)

Status: OPEN
Component: `personal_index/content_summarizer.py` (`summarize` / `_score_and_select`, line 132) and `personal_index/content_search.py` (`SearchIndex.search`, line ~488 offset slice)
Umbrella: ARCH-2 (#983)
Issue: (none — this is a class-rule extension; the per-site instances are the OPEN QA issues below)
Binding decision for: the negative-slice-truncation class — EXTENDS the existing **Negative-slice guard (binding)** rule in `docs/CONTRACTS.md` (single home = ARCH-17) to cover the OFFSET slice form
Class: guard-the-caller-supplied-bound — sibling to ARCH-64 (guard-the-raw-divisor), ARCH-58 (pagination `per_page`), ARCH-59 (throttle `window_seconds`); the negative-slice-truncation class is ARCH-17
Docs: `docs/CONTRACTS.md` (extend the Negative-slice guard rule + How-to-apply step, this design PR); `docs/content-summarizer.md` + `docs/content-search.md` (component entries, implementer's fix PR)

## Problem
The negative-slice "top N / limit" defect class (QA-1 `extract_top_n`, QA-2
`tfidf`/`index.search`, QA-3 `Feed.get_recent_entries`, QA-4 13-site sweep,
QA-5 9-site sweep — all CLOSED) has TWO NEW public sites missed by those
sweeps, both confirmed leaking at HEAD:

| module | function | idiom | issue |
|--------|----------|-------|-------|
| content_summarizer.py | `summarize` (via `_score_and_select`) | `scored[:max_sentences]` | QA-15 #1186 |
| content_search.py | `SearchIndex.search` | `ranked[offset:offset + limit]` | QA-16 #1191 |

A NEGATIVE caller-supplied bound leaks Python negative-slice semantics:
`lst[:-1]` returns **all-but-last** instead of an empty list. The `0` bound is
already correct (returns `[]`); the negative bound is not.

- **QA-15 #1186**: `summarize(text, max_sentences=-1)` returns 5 sentences
  (all-but-last of 6) instead of `[]`.
- **QA-16 #1191**: `SearchIndex.search(token, limit=-1)` returns 2 results
  (all-but-last of 3) instead of `[]`. Reachable via public
  `PersonalIndexApp.search(query, limit=-1)`.

## Why this is an EXTENSION, not a new rule (RE-VERIFY finding)
The **Negative-slice guard (binding)** rule ALREADY EXISTS in
`docs/CONTRACTS.md` (single home = ARCH-17) and covers `list[:N]` with
`N < 0 -> []`. Creating a second "Top-N / limit guard (binding)" rule would be
a duplicate, violating the single-home principle the role split exists to
enforce. The genuine gap: the existing rule names only the `list[:N]` idiom.
QA-16 #1191 uses the **OFFSET form** `list[offset:offset+N]`, which the rule
does not explicitly cover. This ticket extends the existing rule to name both
forms and registers the two new instances. It does NOT re-open ARCH-17 or
ARCH-64.

## Binding decision (extends the existing Negative-slice guard rule)
Any "top N / limit / max_*" helper that truncates a ranked list by a
caller-supplied bound MUST guard the bound in BOTH slice forms:

- **`N <= 0` -> return `[]`** (empty result; no negative-slice leak, no
  exception). This covers the zero bound (already correct) AND the negative
  bound (the leak).
- **`N > 0` -> `lst[:N]`** (plain form) **or `lst[offset:offset+N]`**
  (offset form).

The guard short-circuits BEFORE the slice; it must NOT leak
`lst[:-1]` = all-but-last. This is the same "guard the caller-supplied bound"
class as ARCH-64 (guard the raw divisor): a helper that indexes/slices by a
caller-supplied scalar clamps non-positive bounds to a defined empty result
instead of leaking negative-slice semantics or raising.

## Public contract (per-site targets)
`content_summarizer.summarize(text, max_sentences) -> SummaryResult`:
- **Guard path:** `max_sentences <= 0` -> `SummaryResult(sentences=[], summary="", word_count_summary=0)` (short-circuits before the slice; no all-but-last leak).
- **Normal path:** `max_sentences > 0` -> first `max_sentences` scored sentences.
- **Side effects:** none.

`content_search.SearchIndex.search(query, limit, offset=0) -> dict`:
- **Guard path:** `limit <= 0` -> `{"results": [], "total": <total matches>, "query": query}` (short-circuits before the offset slice; `total` is still the full match count, same as `limit == 0`).
- **Normal path:** `limit > 0` -> `{"results": ranked[offset:offset+limit], "total": <total matches>, "query": query}`.
- **Side effects:** none.

## Worked examples
- `summarize(text, max_sentences=0)` -> `sentences == []` (already correct).
- `summarize(text, max_sentences=-1)` -> `sentences == []` (guard; NOT all-but-last).
- `summarize(text, max_sentences=3)` -> first 3 sentences.
- `SearchIndex.search(token, limit=0)` -> `results == []` (already correct).
- `SearchIndex.search(token, limit=-1)` -> `results == []` (guard; NOT all-but-last).
- `SearchIndex.search(token, limit=3, offset=0)` -> first 3 ranked results.

## Guard inputs
- `max_sentences == 0` -> `[]`.
- `max_sentences < 0` (e.g. `-1`) -> `[]`.
- `max_sentences > 0` -> first N.
- `limit == 0` -> `results == []`.
- `limit < 0` (e.g. `-1`) -> `results == []`.
- `limit > 0` -> `ranked[offset:offset+limit]`.

## Acceptance criteria
1. `summarize(text, max_sentences=-1)` returns `SummaryResult` with
   `sentences == []`, `summary == ""`, `word_count_summary == 0` (does NOT
   return all-but-last).
2. `summarize(text, max_sentences=0)` still returns `sentences == []` (zero
   bound unchanged).
3. `summarize(text, max_sentences=3)` returns the first 3 sentences.
4. `SearchIndex.search(token, limit=-1)` returns `results == []` with
   `total == <full match count>` (does NOT return all-but-last).
5. `SearchIndex.search(token, limit=0)` still returns `results == []` (zero
   bound unchanged).
6. `SearchIndex.search(token, limit=3, offset=0)` returns the first 3 ranked
   results.
7. The guard is stated in each function's contract docstring (part 1, guard
   paths) and the `docs/CONTRACTS.md` Negative-slice guard rule names BOTH
   slice forms (`list[:N]` and `list[offset:offset+N]`).

## Pinning tests to add
The implementer adds ONE pinning test per site asserting the returned object
for the guard input ALONGSIDE the normal case (guard-path pin):
- `test_summarize_max_sentences_negative_returns_empty`:
  `summarize(text, max_sentences=-1).sentences == []` (guard) — the existing
  xfail-strict `test_summarize_max_sentences_negative_returns_empty` /
  `test_summarize_max_sentences_more_negative_returns_empty` in
  `tests/deep/test_content_summarizer_adversarial.py` flip to hard passes.
- `test_searchindex_search_limit_negative_returns_empty`:
  `SearchIndex.search(token, limit=-1)["results"] == []` (guard) — the
  existing xfail-strict `test_searchindex_search_limit_negative_returns_empty`
  / `test_app_search_limit_negative_returns_empty` in
  `tests/deep/test_app_adversarial.py` flip to hard passes.

## Docs update (same PR)
`docs/CONTRACTS.md` — EXTEND the existing **Negative-slice guard (binding)**
rule to name both slice forms (`list[:N]` AND `list[offset:offset+N]`) and
add the two new per-site instances (QA-15 #1186, QA-16 #1191) to its
per-site list; add a matching **How to apply** step for the offset form (this
design PR). `docs/content-summarizer.md` + `docs/content-search.md` — the
`summarize` / `SearchIndex.search` Contract-holes entries are updated by the
implementer in the SAME PR that lands the code fix (state the guard:
`N <= 0 -> []`, positive -> `lst[:N]` / `lst[offset:offset+N]`; remove the
Contract-holes bullet once merged).

## Class reference
This rule EXTENDS the single home for the negative-slice-truncation class
(ARCH-17) to cover the offset slice form. Sibling class rules: ARCH-64
(guard-the-raw-divisor), ARCH-58 (pagination `per_page`), ARCH-59 (throttle
`window_seconds`). Per-site instances (the implementer's claim queue, kept
OPEN): QA-15 #1186 (content_summarizer.summarize `max_sentences`), QA-16
#1191 (content_search.SearchIndex.search `limit`). Do NOT re-open ARCH-17 or
ARCH-64.
