# `personal_index.pipeline_runner` — spec

The full-pipeline orchestrator. `PipelineRunner` wires together the six
crawl→extract→filter→score→tag→index stages and drives them over either
seed URLs (`run`) or local files (`run_from_files`), accumulating a
`PipelineStats` and emitting progress through an optional callback.

> **Module identity (near-name disambiguation):** this page documents
> `personal_index/pipeline_runner.py` — the `PipelineRunner` / `PipelineStats`
> orchestrator. It is **distinct from** `personal_index/pipeline_orchestrator.py`
> (the `PipelineOrchestrator` + `PipelineResult` class documented on
> [pipeline-orchestrator.md](pipeline-orchestrator.md)). The two are separate
> modules with separate public classes; the tests import this one:
> `tests/test_pipeline_stages.py:8` does
> `from personal_index.pipeline_runner import PipelineRunner`.

## Public surface

Line numbers refer to `personal_index/pipeline_runner.py`.

| symbol | line | signature | notes |
|--------|------|-----------|-------|
| `PipelineStats` | 25 | `@dataclass` | per-stage counters + `errors: list[str]` + `elapsed_seconds` |
| `PipelineStats.summary` | 40 | `() -> str` | human-readable multi-line summary |
| `PipelineRunner` | 59 | class | the orchestrator |
| `PipelineRunner.__init__` | 66 | `(data_dir=".personal_index", pipeline_config=None, progress_callback=None)` | creates dirs, stores, processors, crawler |
| `PipelineRunner.run` | 286 | `(seed_urls, max_depth=None, stages=None) -> PipelineStats` | crawl-driven entry |
| `PipelineRunner.run_from_files` | 324 | `(file_paths, stages=None) -> PipelineStats` | file-driven entry (crawl stage = `_read_files`) |
| `PipelineRunner.add_page_directly` | 465 | `(page: CrawledPage) -> bool` | single-page fast path (skip crawl) |
| `PipelineRunner.close` | 505 | `() -> None` | close crawler/index, save tag+interest stores |

Private stage methods: `_stage_crawl` (136), `_stage_extract` (162),
`_stage_filter` (188), `_stage_score` (214), `_stage_tag` (239),
`_stage_index` (265). Each takes the previous stage's page list, mutates
`stats`, and returns the surviving page list.

## Invariants

- **Sequential data flow.** Each stage consumes the *previous* stage's output
  list. `run`/`run_from_files` thread `pages` through the six stages in
  fixed order (crawl → extract → filter → score → tag → index).
- **Per-page error isolation.** Every stage wraps its per-page work in
  `try/except (RuntimeError, OSError)` and appends to `stats.errors` rather
  than aborting the run.
- **`elapsed_seconds` always set.** Both entry points set it in a `finally`
  block, so it is populated even when a stage raises.
- **`min_score_threshold` gate at index time.** `_stage_index` (265) and
  `add_page_directly` (465) both drop a page when
  `page.relevance_score < pipeline_config.min_score_threshold`; the index
  stage counts those drops into `pages_filtered_out`.
- **Guard inputs.** `run([])` → all counters 0, `errors == []`.
  `add_page_directly` returns `False` for an empty-content page, a page the
  filter rejects, or a page below the score threshold.

## Known contract hole

- **`stages` is documented as an arbitrary "subset" but only a *prefix* of
  the canonical order produces meaningful results.** See
  [ARCH-91](../tickets/ARCH-91.md).
