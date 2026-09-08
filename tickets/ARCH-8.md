Status: OPEN
Kind: ARCH
Author: architect (cycle 173)
Issue: #1010

# ARCH-8: `PipelineOrchestrator` dead `_stage_*` methods

## Component
`personal_index.pipeline_orchestrator.PipelineOrchestrator`
(pipeline_orchestrator.py, lines 168–193).

## Symptom
`_stage_filter`, `_stage_score`, `_stage_tag`, and `_stage_index` are defined
but **never called** anywhere in the module or the repo (verified: the only
other `_stage_*` method, `_stage_read`, is called at line 307 by
`run_from_files`; the four above have zero call sites). The live stage path is
the `_run_*_stage` + `_apply_*` pair, driven by `_execute_stages` (lines
229–232). A reader of the class would reasonably assume the four `_stage_*`
methods are the stage implementations, but they are dead — the live
implementations are `_apply_filter`/`_apply_score`/`_apply_tag`/`_apply_index`
wrapped by `_run_stage`. This is a genuine class-(b) contract hole: four
public-looking methods that do nothing.

## Public contract (the code is the truth)
- The live stage path is `_execute_stages` → `_run_filter_stage` →
  `_run_score_stage` → `_run_tag_stage` → `_run_index_stage`, each calling
  `_run_stage(items, stage_fn, name)` with the matching `_apply_*` callback.
- `_stage_filter`, `_stage_score`, `_stage_tag`, `_stage_index` are not
  referenced by any code path.

## Acceptance criteria
- The four dead `_stage_*` methods are removed (they are dead), OR — if the
  operator prefers to keep them — they are wired into the live path so the
  `_run_*_stage`/`_apply_*` duplication is eliminated (one implementation per
  stage, not two). Either way, `docs/pipeline-orchestrator.md` is updated to
  match the chosen resolution (remove the four from the "Private helpers"
  list, or reword it to state which of the two implementations is live).
- After the change there is exactly ONE implementation per stage (filter,
  score, tag, index); no stage has both a `_stage_*` and an `_apply_*` body.

## Pinning tests to add
`test_stage_methods_are_the_live_path` — run `PipelineOrchestrator`
(`run_from_files` on one temp file, or `run` on a stubbed crawler) and assert
the stage counters (`pages_passed_filter`, `pages_scored`, `pages_tagged`,
`pages_indexed`) reflect the live path. Alongside, a guard-path input (a file
that fails the content filter) asserting the filtered-out counter increments —
one test pins both the live-path behavior and the guard (drop) path, so a
regression that re-introduces a dead/alternate stage path is caught.

## Docs page it updates
`docs/pipeline-orchestrator.md` (the "Private helpers" `_stage_*` entries +
the contract-holes line, which this ticket resolves).
