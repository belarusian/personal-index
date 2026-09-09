# ARCH-56 — link_analyzer: `get_aggregate_stats` undercounts `unique_external_domains` (unions the top-20-truncated `domain_distribution`)

Status: OPEN
Component: `personal_index/link_analyzer.py` — `LinkAnalyzer.get_aggregate_stats`, `LinkAnalyzer.analyze`, `LinkAnalysisResult`
Umbrella: ARCH-2 (#983)
Issue: #1172
Docs: `docs/link-analyzer.md` (Contract Holes)

## Problem
`get_aggregate_stats` computes `unique_external_domains` as the size of the
union of `r.stats.domain_distribution.keys()` across all results. But
`analyze` populates `stats.domain_distribution` with only the **top-20**
external domains:

    stats.domain_distribution = dict(domain_counter.most_common(20))

So when any page in the batch has more than 20 distinct external domains, the
21st and beyond are dropped from `domain_distribution` and are **never seen by
the aggregate**. `unique_external_domains` is therefore silently smaller than
the true number of distinct external domains across the batch.

The per-page `LinkStats.unique_domains` field is correct — it is
`len(domain_counter)`, the full count. Only the cross-page aggregate is wrong,
which makes the bug easy to miss: a single-page analysis looks right, and the
aggregate is only wrong once a page exceeds the top-20 cap. The existing
`test_aggregate_stats` never asserts `unique_external_domains` and uses a
single external domain per page, so the hole is untested.

## Public contract (target)
Add a field to `LinkAnalysisResult` that carries the **full** set of external
domains for the page (not truncated), and have `get_aggregate_stats` union
that instead of the truncated distribution:

- `LinkAnalysisResult.all_external_domains: set[str] = field(default_factory=set)`
  — the complete set of distinct external domains seen on the page
  (`set(domain_counter.keys())`), populated in `analyze` alongside
  `stats.domain_distribution`.
- `get_aggregate_stats`: compute
  `unique_external_domains` as
  `len(set().union(*[r.all_external_domains for r in results]))` (or an
  equivalent loop that unions `r.all_external_domains`), **not**
  `len(union of r.stats.domain_distribution.keys())`.

`stats.domain_distribution` keeps its top-20 truncation (it is a
human-readable distribution, not the source of truth for the aggregate). The
new field is additive with a default, so existing construction of
`LinkAnalysisResult` (and existing tests) is unchanged.

## Behavior
- For a batch where one page has 25 distinct external domains and another has
  3 (with 2 overlapping), `get_aggregate_stats` returns
  `unique_external_domains == 26` (the true union), not `20 + 3 - 2 = 21`
  (the truncated union).
- For a batch where every page has <= 20 distinct external domains, the result
  is unchanged from today (the truncated distribution already holds all
  domains).
- `analyze` still sets `stats.domain_distribution` to the top-20 and
  `stats.unique_domains` to the full `len(domain_counter)`; both are
  unchanged.

## Guard inputs
- `get_aggregate_stats([])` (empty results list) — `unique_external_domains ==
  0` (the union of nothing), `pages_analyzed == 0`; no exception.
- A page whose links are all internal (no external domains) —
  `all_external_domains == set()`; contributes nothing to the union.
- A page with a single external domain — `all_external_domains` is a
  one-element set; aggregate matches today's value.

## Acceptance criteria
1. For a batch where one page has > 20 distinct external domains,
   `get_aggregate_stats(results)["unique_external_domains"]` equals the true
   number of distinct external domains across the batch (the full union), not
   the truncated union.
2. For a batch where every page has <= 20 distinct external domains,
   `unique_external_domains` is unchanged from the current behavior.
3. `get_aggregate_stats([])` returns `unique_external_domains == 0` and
   `pages_analyzed == 0` without raising.
4. `analyze` still sets `stats.domain_distribution` to the top-20 entries and
   `stats.unique_domains` to `len(domain_counter)` (existing tests still
   pass).
5. `LinkAnalysisResult` constructed without `all_external_domains` (existing
   call sites) defaults to `set()` and does not raise.

## Pinning tests to add
- `test_aggregate_unique_external_domains_exceeds_top20_cap`: build one page
  with 25 distinct external domains (e.g. `http://d{i}.com` for `i` in
  `range(25)`) and a second page with 3 domains, 2 of which overlap the first
  page; run `analyze_batch` then `get_aggregate_stats`; assert
  `unique_external_domains == 26` (the true union) — this is the regression
  that the current top-20-truncated union gets wrong (it would return 21).
- `test_aggregate_unique_external_domains_under_cap_unchanged`: build a batch
  where every page has <= 20 distinct external domains; assert
  `unique_external_domains` equals the true union (matches current behavior).
- `test_aggregate_empty_results`: `get_aggregate_stats([])` returns
  `unique_external_domains == 0` and `pages_analyzed == 0`.

## Docs update (same PR)
`docs/link-analyzer.md` — `LinkAnalysisResult` entry: add the
`all_external_domains` field; `get_aggregate_stats` entry: state that
`unique_external_domains` is now the union of the full per-page external
domain sets (not the truncated `domain_distribution`), so it is the true
distinct count. Remove/adjust the Contract-holes bullet for this hole once
merged.
