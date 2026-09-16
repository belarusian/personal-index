# ARCH-91: run/run_from_files `stages` is documented as an arbitrary "subset" but only a prefix of the canonical order produces meaningful results

Status: CLAIMED 2026-09-16
Component: personal_index/pipeline_runner.py
Issue: #1471

## Symptom

`PipelineRunner.run` (line 286) and `run_from_files` (line 324) both document
their `stages` argument as:

    stages: Optional set of stage names to run (subset of
        {"crawl", "extract", "filter", "score", "tag", "index"}).
        None runs every stage (the default).

The word "subset" implies any combination of stage names can be selected
independently. But the body is a **sequential pipeline**: each stage consumes
the *previous* stage's output list, and the six stages are threaded in fixed
order (crawl → extract → filter → score → tag → index). So a stage that is
not part of a *prefix* of that order receives an empty input list and does
nothing. Selecting a non-prefix subset (e.g. `stages={"index"}`, or
`stages={"score","index"}`) silently no-ops: no pages are crawled, so nothing
reaches the later stages, and the run returns all-zero counters with no error.

The docstring over-promises "subset" where the code only honors "prefix".

## Evidence

`run` (lines 304-317) threads `pages` through the stages in order:

    304    if stages is None or "crawl" in stages:
    305        pages = self._stage_crawl(seed_urls, max_depth, stats, self._emit_progress)
    306    else:
    307        pages = []
    308    if stages is None or "extract" in stages:
    309        pages = self._stage_extract(pages, stats, self._emit_progress)
    ...
    316    if stages is None or "index" in stages:
    317        self._stage_index(pages, stats, self._emit_progress)

When `"crawl"` is absent, `pages = []` (line 307), so every downstream stage
operates on an empty list. `run_from_files` has the identical structure
(lines 338-350, with `_read_files` standing in for `_stage_crawl`).

The behavior is already pinned (and therefore the *current* behavior is
witnessed, not the docstring's promise) by the validator's deep test
`tests/deep/test_pipeline_runner_adversarial.py`:

    def test_run_index_only_stage_subset(tmp_path):
        r = PipelineRunner(data_dir=str(tmp_path / "dd"))
        st = r.run(["http://example.com"], stages={"index"})
        assert st.pages_crawled == 0
        assert st.pages_indexed == 0
        r.close()

    def test_run_unknown_stage_degrades_gracefully(tmp_path):
        ...
        st = r.run(["http://example.com"], stages={"bogus_stage"})
        assert st.pages_crawled == 0
        assert st.pages_indexed == 0
        assert st.errors == []

So `stages={"index"}` (a non-prefix subset) yields `pages_indexed == 0` — the
"index" stage the caller asked for did not index anything.

## Why it matters

A caller who reads the docstring and passes `stages={"index"}` (or any
non-prefix subset) to index already-crawled pages gets a silent no-op with no
error and no log warning. The documented "subset" contract and the actual
"prefix-only" behavior disagree, and the disagreement is silent.

## Proposed fix (implementer)

Two acceptable resolutions — pick one and make the docstring and behavior
agree:

1. **Document the prefix contract (minimal, doc-only).** Reword the `stages`
   docstring in both `run` (line 293) and `run_from_files` (line 330) to state
   the EXACT behavior: the stages run in the fixed order
   crawl → extract → filter → score → tag → index, and a stage only receives
   the output of the preceding stage; therefore a meaningful selection is a
   *prefix* of that order, and a non-prefix subset (e.g. `{"index"}`) runs
   with an empty input and indexes nothing. State that an unknown stage name
   is ignored (graceful no-op, no error). Do NOT change the code.
2. **Make `stages` a true subset (code change).** Only if the product intent
   is independent stage selection — this would require a source of input pages
   for non-first stages (e.g. a `pages` parameter or a persisted crawl), which
   is a larger design change and is NOT the minimal fix.

The minimal additive fix is option 1: correct the docstring to the exact
prefix contract. The behavior is already correct and already pinned by the
deep test; only the docstring over-promises.

## Acceptance criteria

1. The `stages` docstring in `run` (line 293) and `run_from_files` (line 330)
   states that stages run in the fixed order crawl → extract → filter → score
   → tag → index and that each stage consumes the previous stage's output, so
   a meaningful selection is a prefix of that order.
2. The docstring states that a non-prefix subset (e.g. `{"index"}`) runs with
   an empty input and produces no indexed pages, and that an unknown stage
   name is ignored without raising.
3. No code behavior change: `run(["url"], stages={"index"})` still returns
   `pages_crawled == 0` and `pages_indexed == 0`; `run(["url"],
   stages={"bogus"})` still returns all-zero counters and `errors == []`.
4. The existing deep tests `test_run_index_only_stage_subset` and
   `test_run_unknown_stage_degrades_gracefully` still pass unchanged.

## Pinning tests to add (tests/test_pipeline_runner.py)

- `test_run_non_prefix_stage_subset_no_op`: with a mocked crawler that returns
  a page, `run(["http://example.com"], stages={"index"})` returns
  `pages_crawled == 0` and `pages_indexed == 0` (the "index" stage the caller
  named did not index anything because crawl was skipped). This pins the
  corrected docstring claim against the returned `PipelineStats` object.
- `test_run_prefix_subset_runs_through`: `run(["http://example.com"],
  stages={"crawl","extract","filter","score","tag","index"})` (the full
  prefix) with a mocked crawler returns `pages_crawled >= 1` and
  `pages_indexed >= 1` (guard path: the full prefix is the only selection that
  reaches index). One returned object pins both the prefix behavior and the
  non-prefix no-op.

## Docs update (same PR)

`docs/pipeline-runner.md` (new spec page) documents the `run` /
`run_from_files` contract and calls out this hole under "Known contract
hole"; `docs/README.md` gains the index entry.
