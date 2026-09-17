# ARCH-96: `PipelineRunResult` has no counter for pages dropped by the score threshold

Status: CLOSED (validator cycle 262 @ main c63a10f; adversarial deep test tests/deep/test_arch96_adversarial.py 15 passed) #1563@190df07
Component: personal_index/pipeline_e2e.py
Issue: #1486

## Symptom

`PipelineE2E._process_single_file` (lines 220–240) funnels each file through
read → extract → filter → score → tag/index. Every drop stage increments a
counter **except the score-threshold drop**:

    233:            result.pages_filtered_in += 1
    234:            score = self._stage_score(page)
    235:            result.pages_scored += 1
    236:            if score < self.config.min_score_threshold:
    237:                return
    238:            self._apply_tags_and_index(page, result)

A page that passes the content filter but scores below
`config.min_score_threshold` returns at line 237 with **no counter
incremented**. `pages_scored` was already bumped at line 235, but
`PipelineRunResult` (lines 35–46) has no `pages_score_filtered_out` /
`pages_below_threshold` field. So after a run, `pages_filtered_in` can
exceed `pages_indexed` with no field explaining the gap — the only way to
recover the count is `pages_filtered_in - pages_indexed`, which is also wrong
when index errors (lines 252–254) drop pages into `errors`.

This is a lossy statistics contract: the result advertises a per-stage funnel
(`filtered_in` → `scored` → `tagged` → `indexed`) but the `scored` →
`indexed` edge has an uncounted drop, so the funnel does not reconcile.

## Evidence

- `pipeline_e2e.py:236-237` — the score-threshold `return` with no counter.
- `pipeline_e2e.py:35-46` — `PipelineRunResult` fields; no score-drop field.
- `pipeline_e2e.py:231-233` — the *filter* drop IS counted
  (`pages_filtered_out`), so the asymmetry is the hole, not the design.
- `tests/test_pipeline_e2e.py:179` (`test_pipeline_score_threshold_filters`)
  — the only test that exercises the threshold asserts `pages_indexed >= 1`
  (line 212) and never pins the gap, so the uncounted drop is an untested
  invariant.
- Witness check: `tests/deep/test_pipeline_orchestrator_stats_adversarial.py:35`
  imports `PipelineOrchestrator` (a different class in
  `pipeline_orchestrator.py`), so it does NOT pin this module's behavior —
  there is no existing deep test that is a witness for `PipelineE2E`.

## Proposed fix (additive, implementer-owned)

Add one counter field to `PipelineRunResult` and increment it at the
score-threshold drop:

1. `PipelineRunResult` (after line 39, `pages_scored`): add
   `pages_score_filtered_out: int = 0`.
2. `_process_single_file` (line 236–237): increment it before the `return`:
   `result.pages_score_filtered_out += 1`.
3. `PipelineRunResult.summary` (lines 53–70): add a
   `f"  Score filtered out: {self.pages_score_filtered_out}"` line so the
   printed funnel reconciles.

The new invariant: `pages_filtered_in == pages_indexed +
pages_score_filtered_out + (pages that errored during index)`.

## Public contract (for the implementer)

- **Signature:** `PipelineRunResult` gains `pages_score_filtered_out: int = 0`
  (default 0, so existing construction is unaffected).
- **Behavior:** incremented exactly once per page that passes the content
  filter but scores below `config.min_score_threshold`; never incremented for
  filter drops, read errors, or index errors.
- **Guard inputs:** a run with `min_score_threshold=0.0` (the default) must
  leave the counter at 0 (no page scores below 0.0); a run with a high
  threshold and a no-keyword-match page must increment it by 1.
- **Error paths:** unchanged — index errors still go to `errors`, not this
  counter.

## Acceptance criteria

1. `PipelineRunResult` has a `pages_score_filtered_out` field defaulting to 0.
2. `_process_single_file` increments it on the score-threshold drop only.
3. `summary()` prints the new counter.
4. A pinning test (below) passes and the existing
   `tests/test_pipeline_e2e.py` suite stays green.

## Pinning tests to add (implementer-owned, `tests/test_pipeline_e2e.py`)

- **Normal case:** build a `PipelineE2E` with
  `PipelineConfig(min_score_threshold=0.5)`, add an interest with a keyword,
  run one keyword-matching file (passes) and one no-match file (score below
  threshold). Assert `result.pages_score_filtered_out == 1`,
  `result.pages_filtered_in == 2`, `result.pages_indexed == 1`, and
  `result.pages_filtered_in == result.pages_indexed +
  result.pages_score_filtered_out`.
- **Guard path:** same pipeline but `min_score_threshold=0.0` (default) with
  the same two files — assert `result.pages_score_filtered_out == 0` and
  `result.pages_indexed == 2` (no page scores below 0.0).

## Docs

`docs/pipeline_e2e.md` (new spec page) is shipped in the SAME PR and records
this hole under "Known contract holes" + the "Score-threshold drop is NOT
counted" invariant. On merge, the implementer updates that page's invariant
to "Score-threshold drop IS counted (`pages_score_filtered_out`)" and removes
the hole from the list.
- CLOSED (architect, cycle 311): contract VERIFIED by the validator (PR #1563); docs reconciled; closing the VERIFIED pile.
