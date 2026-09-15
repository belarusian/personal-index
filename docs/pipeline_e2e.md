# `personal_index.pipeline_e2e` — spec

End-to-end pipeline orchestrator. `PipelineE2E` wires the individual
components (extract → filter → score → tag → index → search) into one
object that can be driven from the CLI or programmatically against local
files, and `PipelineRunResult` is the per-run statistics record it returns.
State is persisted under `data_dir` (interests/tags/search-index JSON files).

> **Module identity (near-name disambiguation):** this page documents
> `personal_index/pipeline_e2e.py` — the `PipelineE2E` orchestrator and its
> `PipelineRunResult` dataclass. It is **distinct from**
> `personal_index/pipeline_orchestrator.py` (the `PipelineOrchestrator`
> class with the `stats.pages_tagged`/`pages_indexed` single-source counters
> audited in ARCH-9) and from `personal_index/pipeline.py` (the `Pipeline`
> / `PipelineRunner` classes driven by the `pipeline` CLI command).
> `tests/test_pipeline_e2e.py:12` does
> `from personal_index.pipeline_e2e import PipelineE2E`; the deep test
> `tests/deep/test_pipeline_orchestrator_stats_adversarial.py:35` imports
> `PipelineOrchestrator` (the *other* class), so it is **not** a witness for
> this module.

## Public surface

Line numbers refer to `personal_index/pipeline_e2e.py`.

| symbol | line | signature | returns / behavior |
|--------|------|-----------|--------------------|
| `PipelineRunResult` | 32 | `@dataclass` | Per-run stats (see fields below). |
| `PipelineRunResult.success` | 49 | `@property -> bool` | `len(self.errors) == 0`. |
| `PipelineRunResult.summary` | 53 | `() -> str` | Human-readable multi-line summary of the counters. |
| `PipelineE2E` | 74 | class | The orchestrator. |
| `PipelineE2E.__init__` | 86 | `(data_dir: str = ".personal_index", config: PipelineConfig \| None = None) -> None` | Creates `data_dir` + `cache`/`archive`/`backups` subdirs; builds `InterestStore`, `TagStore`, `SearchIndex`, `ContentExtractor`, `ContentScorer`, `ContentFilter`. |
| `PipelineE2E.add_interest` | 121 | `(name: str, keywords: list[str] \| None = None, priority: int = 5) -> None` | Adds an `Interest` to the store. |
| `PipelineE2E.run_from_files` | 202 | `(file_paths: list[str]) -> PipelineRunResult` | Runs every file through all stages; returns the accumulated `PipelineRunResult`. |
| `PipelineE2E.search` | 256 | `(query: str, limit: int = 20) -> list[dict[str, Any]]` | Searches the index; returns dicts with `url`/`title`/`score`/`snippet`/`tags`. |
| `PipelineE2E.close` | 278 | `() -> None` | Persists the search index, tag store and interest store. |

### `PipelineRunResult` fields (lines 35–46)

`pages_crawled`, `pages_extracted`, `pages_filtered_in`, `pages_filtered_out`,
`pages_scored`, `pages_tagged`, `pages_indexed`, `tags_applied`,
`interests_matched`, `errors: list[str]`, `elapsed_seconds: float`,
`indexed_pages: list[CrawledPage]`.

## Invariants

- **Per-file funnel** (`_process_single_file`, lines 220–240): a file is
  read → extracted → filtered → scored → (tagged + indexed). Each stage that
  keeps the page increments its counter; each stage that drops it increments
  its drop counter **except the score-threshold drop** (see contract hole).
- **Filter drop is counted** (lines 231–233): a page failing
  `content_filter.should_include` increments `pages_filtered_out` and returns.
- **Score-threshold drop is NOT counted** (lines 235–237): a page that passes
  the filter but scores below `config.min_score_threshold` returns with **no
  counter incremented** — `pages_scored` was already incremented at line 235,
  but there is no `pages_score_filtered_out` / `pages_below_threshold` field.
- **Tag/index are coupled** (`_apply_tags_and_index`, lines 242–254):
  `pages_tagged` increments only when at least one tag is produced;
  `pages_indexed` increments only when `search_index.add_page` succeeds.
- **Errors are non-fatal** (lines 239–240, 252–254): `RuntimeError`/`OSError`
  during processing and `OSError`/`ValueError` during indexing are appended to
  `result.errors` and the run continues; `success` is `False` iff `errors` is
  non-empty.

## Known contract holes

- **Score-threshold drop is uncounted** (ARCH-96): a page that passes the
  content filter but scores below `min_score_threshold` is dropped at
  lines 236–237 with no counter, so `pages_filtered_in` can exceed
  `pages_indexed` with no field explaining the gap. The existing test
  `tests/test_pipeline_e2e.py::test_pipeline_score_threshold_filters`
  (line 179) asserts only `pages_indexed >= 1` and never pins the gap, so the
  invariant "every filtered-in page is either indexed or counted as
  score-filtered" is untested.
