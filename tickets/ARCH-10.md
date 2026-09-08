Status: OPEN
Kind: ARCH
Author: architect (cycle 174)
Issue: #1015

# ARCH-10: `cli._print_pipeline_stats` reads a non-existent `PipelineStats` field

## Component
`personal_index.cli._print_pipeline_stats` (cli.py, line 632) and
`personal_index.models.PipelineStats` (models.py, line 461).

## Symptom
`_print_pipeline_stats` echoes `stats.pages_filtered_in` (line 632).
`PipelineStats` has **no** `pages_filtered_in` field and **no** such property —
the field is `pages_passed_filter` (models.py line 473). So any
`personal-index pipeline` run that reaches the stats print (i.e. every
successful run) raises `AttributeError: 'PipelineStats' object has no
attribute 'pages_filtered_in'`. This is the same `pages_filtered_in` vs
`pages_passed_filter` drift that ARCH-3 fixed in `docs/API_REFERENCE.md`, but
here it is in **code**, not docs.

## Public contract (the code is the truth)
`PipelineStats` fields (models.py line 461), in order: `pages_crawled`,
`pages_extracted`, `pages_passed_filter`, `pages_filtered_out`,
`pages_scored`, `pages_tagged`, `pages_indexed`, `tags_applied`, `errors`,
`elapsed_seconds`. There is no `pages_filtered_in` attribute.
`_print_pipeline_stats(stats) -> None` must read `stats.pages_passed_filter`
for the "Filtered in:" line.

## Acceptance criteria
- `_print_pipeline_stats` reads `stats.pages_passed_filter` (not
  `pages_filtered_in`) for the "Filtered in:" line.
- `personal-index pipeline <url>` (or `--import-file`) completes and prints
  the stats block without raising `AttributeError`.
- `docs/cli.md` "Private helpers" `_print_pipeline_stats` entry and the
  contract-holes line are updated to reflect the fix (the "Bug" note is
  removed / marked resolved).

## Pinning tests to add
`test_print_pipeline_stats_uses_pages_passed_filter` — call
`_print_pipeline_stats(PipelineStats(pages_crawled=1, pages_passed_filter=2,
pages_filtered_out=3, ...))` with `capsys` and assert the captured output
contains `Filtered in: 2` (the `pages_passed_filter` value) and does NOT
contain `AttributeError`. Alongside, a guard/default input:
`_print_pipeline_stats(PipelineStats())` (all zeros) asserting the output
contains `Filtered in: 0` — one test pins both the populated and the default
path, so a regression that re-introduces the wrong field name is caught.

## Docs page it updates
`docs/cli.md` (the `_print_pipeline_stats` helper entry + the contract-holes
line, which this ticket resolves).
