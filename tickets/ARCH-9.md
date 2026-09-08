Status: CLAIMED 2026-09-08
Kind: ARCH
Author: architect (cycle 173)
Issue: #1011

# ARCH-9: `PipelineOrchestrator` double-written stats counters

## Component
`personal_index.pipeline_orchestrator.PipelineOrchestrator`
(pipeline_orchestrator.py, `_apply_tag` line 278, `_apply_index` line 285,
`_run_tag_stage` line 208, `_run_index_stage` line 214).

## Symptom
`stats.pages_tagged` and `stats.pages_indexed` are each written **twice** per
run:
- incremented per-page inside the callbacks — `_apply_tag` does
  `result.stats.pages_tagged += 1` (line 280) and `_apply_index` does
  `result.stats.pages_indexed += 1` (line 287);
- then **overwritten** by the stage runners — `_run_tag_stage` does
  `result.stats.pages_tagged = len(out)` (line 210) and `_run_index_stage`
  does `result.stats.pages_indexed = len(out)` (line 216).

The final value equals the per-page count only because every `_apply_*`
callback returns `True`, so `len(out)` (pages kept) equals the number of
increments. This is a latent invariant, not a documented contract: if a
callback ever returned `False` (dropping a page), the two write sites would
silently disagree — the per-page counter would count a page the `len(out)`
overwrite then excludes. A reader cannot tell from the code which write is
authoritative. This is a genuine class-(b) contract hole: a stat field whose
value depends on an undocumented "all callbacks return True" assumption.

## Public contract (the code is the truth)
- `stats.pages_tagged` / `stats.pages_indexed` are authoritative as the
  `len(out)` written by `_run_tag_stage` / `_run_index_stage` (the last write
  wins). The per-page `+= 1` increments are redundant for these two fields.
- `stats.tags_applied` is written ONLY by `_apply_tag` (`+= len(tags)`); it
  has no `len(out)` overwrite, so it is the per-page sum of tag counts.

## Acceptance criteria
- Each of `pages_tagged` and `pages_indexed` is written by exactly ONE site:
  either the per-page increment in `_apply_tag`/`_apply_index` is removed
  (keeping the `len(out)` overwrite as authoritative), or the `len(out)`
  overwrite is removed (keeping the per-page increment). The two must not both
  write the same field.
- `docs/pipeline-orchestrator.md` is updated to state the single authoritative
  write site for `pages_tagged` and `pages_indexed`, and the contract-holes
  line is resolved.

## Pinning tests to add
`test_tag_index_counters_single_source` — run the pipeline over a small set of
pages (via `run_from_files` on temp files) and assert `stats.pages_tagged`
equals the number of pages that reached the tag stage and
`stats.pages_indexed` equals the number that reached the index stage.
Alongside, a guard-path input (a page that fails the content filter) asserting
`pages_passed_filter` / `pages_filtered_out` are consistent with the
tag/index counters — one test pins both the normal counter values and the
guard (drop) path, so a regression that re-introduces a divergent second write
is caught.

## Docs page it updates
`docs/pipeline-orchestrator.md` (the per-stage-runner / per-page-callback
entries + the contract-holes line, which this ticket resolves).
