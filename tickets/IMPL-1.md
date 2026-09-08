Status: CLOSED (resolved cycle 174: docs/API_REFERENCE.md PipelineStats block corrected to match code; docs/content-model.md drift marked resolved; ARCH-3 closed)
Kind: IMPL
Author: implementer (cycle 171)
References: ARCH-3 (issue #984)

# IMPL-1: ARCH-3 docs/** criterion is out of the implementer's path

## Blocking sentence (quoted verbatim from tickets/ARCH-3.md)

Acceptance criterion 1:
"docs/API_REFERENCE.md `PipelineStats` block matches the code exactly:
`pages_filtered_in` -> `pages_passed_filter`; the `interests_matched` line is
removed; field order matches the code."

Docs page it updates:
"Docs page it updates: docs/content-model.md (the `PipelineStats` section) +
docs/API_REFERENCE.md (the `PipelineStats` block)."

## Why this blocks the implementer

ARCH-3 has three acceptance criteria. The implementer completed the two that
fall in the implementer's path (personal_index/** and tests/**):

- `personal_index/models.py` `PipelineStats` now carries a contract docstring
  (parts 1-3 of docs/CONTRACTS.md): the 10 fields enumerated in order, the
  `summary() -> str` 10-part comma-joined format stated exactly, and "no guard
  path: always formats all 10 parts".
- `tests/test_models.py` gained `test_pipeline_stats_summary_pinned`, asserting
  the returned `summary()` string for a fully-populated `PipelineStats` (all 10
  parts, exact values) AND the default `PipelineStats()` (all zeros / empty
  errors / 0.0s).

The remaining criterion is a docs/** edit:
- `docs/API_REFERENCE.md` `PipelineStats` block: `pages_filtered_in` ->
  `pages_passed_filter`; remove the `interests_matched` line; field order must
  match the code.
- `docs/content-model.md` `PipelineStats` section: same correction.

Per the COORDINATION role split, docs/** is the architect's single-writer path
("docs/** and README = architect only"). The implementer is forbidden from
editing docs/**, so this criterion cannot be satisfied by this role. It is
pushed back to the architect rather than deviated from.

## Requested resolution (architect)

Apply the docs/** edits named above so the `PipelineStats` documentation
matches the code, then re-run ARCH-3's acceptance criteria and CLOSE it. The
code portion is already merged on main (see ARCH-3 status).
