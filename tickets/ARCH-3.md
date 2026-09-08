Status: CLAIMED 2026-09-08
Kind: ARCH
Author: architect (cycle 169)
Issue: #984

# ARCH-3: `PipelineStats` docstring + `docs/API_REFERENCE.md` field drift

## Component
`personal_index.models.PipelineStats` (models.py line 461) and
`docs/API_REFERENCE.md` (the `PipelineStats` block, line ~270).

## Symptom
`docs/API_REFERENCE.md` documents `PipelineStats` with fields
`pages_filtered_in` and `interests_matched`. The current code has
`pages_passed_filter` (not `pages_filtered_in`) and **no** `interests_matched`
field. The doc is stale relative to the code.

## Public contract (the code is the truth)
`PipelineStats` (dataclass) fields, in order:
`pages_crawled` (0), `pages_extracted` (0), `pages_passed_filter` (0),
`pages_filtered_out` (0), `pages_scored` (0), `pages_tagged` (0),
`pages_indexed` (0), `tags_applied` (0), `errors` (list, default `[]`),
`elapsed_seconds` (0.0).
- `summary() -> str` — a comma-joined one-line string with exactly 10 parts:
  `crawled=`, `extracted=`, `filtered_in=` (from `pages_passed_filter`),
  `filtered_out=`, `scored=`, `tagged=`, `indexed=`, `tags=` (from
  `tags_applied`), `errors=` (from `len(errors)`), `time=` (from
  `elapsed_seconds`, 1 decimal). **Guard path:** no guard path — always
  formats all 10 parts.

## Acceptance criteria
- `docs/API_REFERENCE.md` `PipelineStats` block matches the code exactly:
  `pages_filtered_in` -> `pages_passed_filter`; the `interests_matched` line is
  removed; field order matches the code.
- `PipelineStats` has a contract docstring (parts 1-3 of docs/CONTRACTS.md):
  the 10 fields enumerated, `summary()`'s 10-part format stated, "no guard
  path".
- ONE pinning test asserts the returned `summary()` string for a populated
  `PipelineStats` (all 10 parts with exact values) AND the default
  `PipelineStats()` (all zeros / empty errors / 0.0s) — the guard/default path.

## Pinning tests to add
`test_pipeline_stats_summary_pinned` (normal + default input), asserting the
returned `summary()` string.

## Docs page it updates
`docs/content-model.md` (the `PipelineStats` section) + `docs/API_REFERENCE.md`
(the `PipelineStats` block).
