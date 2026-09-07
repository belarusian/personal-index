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

## Contract holes found (each -> its own ARCH ticket)
- `PipelineStats` field drift (API_REFERENCE.md vs models.py) -> ARCH-3.
- `SearchIndex.add_page` "Returns page id." vs `len(self._pages)` -> ARCH-4.
- `ValidationRule.validate` blanket docstring -> ARCH-5.
