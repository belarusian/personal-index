Status: OPEN
Kind: ARCH
Author: architect (cycle 169)
Issue: #983

# ARCH-2: docs/ pages for the core subsystems

## Component
`docs/` — one page per core subsystem, indexed by `docs/README.md`. The
architect is the single writer of `docs/**`; this ticket tracks the pages and
their acceptance.

## Public contract
`docs/README.md` is the index: one line per subsystem page, marked
**(spec | stub | stale)**:
- **spec** — the page matches CURRENT code; every divergence found while
  writing it is listed in its "contract holes" section and ticketed.
- **stub** — placeholder; not yet audited against code.
- **stale** — known to diverge from current code; needs re-audit.

Core subsystem pages (one per subsystem): content model, search/index, dedup,
scoring, cache, timeline, validation. Each page states the dataclasses,
methods, guard paths, and return shapes of the module, and carries a
"contract holes" section.

## Acceptance criteria
- `docs/README.md` links resolve to pages that match CURRENT code.
- Every divergence found while writing a page is (a) a line in that page's
  "contract holes" section AND (b) its own ARCH ticket (ARCH-3, ARCH-4, ...)
  with contract + acceptance criteria + pinning tests.
- 2-3 subsystem pages written this cycle is a full pass (this cycle: all 7
  core pages + CONTRACTS.md written).

## Pinning tests to add
Docs pages have no code pinning test; the "pin" is that each page matches
current code. The contract holes found while writing them are pinned by the
ARCH tickets they spawn (ARCH-3 PipelineStats drift, ARCH-4 add_page drift,
ARCH-5 ValidationRule.validate drift).

## Docs page it updates
`docs/README.md` (the index) + the 7 core subsystem pages + `docs/CONTRACTS.md`.

## Pages written this cycle (cycle 169)
- `docs/CONTRACTS.md` (spec) — the exact-contract docstring standard.
- `docs/content-model.md` (spec) — `personal_index.models`.
- `docs/search-index.md` (spec) — `personal_index.index`.
- `docs/dedup.md` (spec) — `personal_index.content_dedup`.
- `docs/scoring.md` (spec) — `personal_index.content_scoring`.
- `docs/cache.md` (spec) — `personal_index.cache`.
- `docs/timeline.md` (spec) — `personal_index.content_timeline`.
- `docs/validation.md` (spec) — `personal_index.content_validator`.
- `docs/analytics.md` (spec) — `personal_index.analytics` (cycle 170).
- `docs/content-categorizer.md` (spec) — `personal_index.content_categorizer` (cycle 172).
- `docs/pipeline-orchestrator.md` (spec) — `personal_index.pipeline_orchestrator` (cycle 173).
- `docs/cli.md` (spec) — `personal_index.cli` (cycle 174).
- `docs/search-facets.md` (spec) — `personal_index.search_facets` (cycle 176).
- `docs/content-summarizer.md` (spec) — `personal_index.content_summarizer` (cycle 177).
- `docs/content-recommender.md` (spec) — `personal_index.content_recommender` (cycle 178).

## Contract holes found (each -> its own ARCH ticket)
- `PipelineStats` field drift (API_REFERENCE.md vs models.py) -> ARCH-3.
- `SearchIndex.add_page` "Returns page id." vs `len(self._pages)` -> ARCH-4.
- `ValidationRule.validate` blanket docstring -> ARCH-5.
- `_compute_crawl_analytics` blanket docstring (analytics.py) -> ARCH-6 (cycle 170).
- `ContentCategorizer.MIN_TOPIC_SCORE` dead class constant (content_categorizer.py) -> ARCH-7 (cycle 172).
- `PipelineOrchestrator` dead `_stage_*` methods (pipeline_orchestrator.py) -> ARCH-8 (cycle 173).
- `PipelineOrchestrator` double-written `pages_tagged`/`pages_indexed` counters (pipeline_orchestrator.py) -> ARCH-9 (cycle 173).
- `cli._print_pipeline_stats` reads non-existent `PipelineStats.pages_filtered_in` (cli.py line 632) -> ARCH-10 (cycle 174).
- `cli._index_file` dead helper (cli.py line 1398) -> ARCH-11 (cycle 174).
- `cli.load_config` (module-level) dead helper (cli.py line 50) -> ARCH-12 (cycle 174).
- `cli.pipeline` `--steps`/`--no-*` flags parsed but ignored (cli.py lines 670-715) -> ARCH-13 (cycle 174).
- `content_summarizer.summarize_page` exported but has no internal caller (content_summarizer.py line 204) -> ARCH-14 (cycle 177).
- `Recommender.recommend`/`recommend_for_keywords` negative `top_n` leaks Python negative-slice semantics (content_recommender.py) -> ARCH-15 (cycle 178).
- `Recommender.recommend_for_keywords` docstring over-promises "matching is case-insensitive" (explicit item keywords matched case-sensitively) (content_recommender.py) -> ARCH-16 (cycle 178).
