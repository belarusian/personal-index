# content_merger — Exact Contract

Module: `personal_index/content_merger.py` (219 lines)

Merges content from multiple sources into a single record, combining text,
tags, and metadata while avoiding duplication. Three public types:
`MergeSource` (an input dataclass), `MergedContent` (the result dataclass),
and `ContentMerger` (the merging engine, selectable by strategy).

## Public API

### MergeSource (dataclass)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| url | str | (required) | Source URL; becomes a member of `MergedContent.sources` |
| title | str | `""` | Source title; candidate for the merged title |
| content | str | `""` | Plain-text body; the merge target |
| tags | list[str] | `[]` | `field(default_factory=list)`; non-str entries are dropped |
| metadata | dict[str, Any] | `{}` | `field(default_factory=dict)`; merged first-writer-wins |
| priority | int | `0` | Higher = more authoritative; sources are sorted by this descending |

#### Methods

- `to_dict() -> dict[str, Any]`
  Returns a plain dict of all six fields, values returned as-is (no copies).

### MergedContent (dataclass)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| url | str | (required) | The primary source's URL (see strategy notes) |
| title | str | (required) | Primary title, else `_best_title` (longest non-empty) |
| content | str | (required) | The merged body (strategy-dependent) |
| tags | list[str] | `[]` | Sorted, lowercased, deduped union of all sources' str tags |
| metadata | dict[str, Any] | `{}` | Merged via `_merge_metadata` (first-writer-wins) |
| source_count | int | `0` | Set to `len(sources)` (the input list length) |
| sources | list[str] | `[]` | All source URLs, in priority-sorted order |
| merge_strategy | str | `"concatenate"` | The **executed** branch name (see contract hole) |

#### Methods

- `to_dict() -> dict[str, Any]`
  Returns a plain dict of all eight fields, values returned as-is (no copies).

### ContentMerger

- `__init__(self, strategy: str = "concatenate")`
  Stores `self.strategy`. **No validation** is performed on `strategy` — any
  string is accepted (see contract hole).

- `merge(self, sources: list[MergeSource]) -> MergedContent | None`
  - **Guard**: if `sources` is empty, return `None` (no merge performed).
  - **Sort**: `sources` are sorted by `priority` descending (stable sort)
    before any strategy runs, so the highest-priority source is `sources[0]`.
  - **Dispatch** on `self.strategy`:
    - `"longest"` → `_merge_longest` — the source with the longest
      `content` (by `len`) wins; its `url`/`title`/`content` are used.
    - `"highest_priority"` → `_merge_highest_priority` — `sources[0]`
      (highest priority) wins; its `url`/`title`/`content` are used.
    - `"unique_paragraphs"` → `_merge_unique_paragraphs` — paragraphs
      (split on `"\n\n"`) are deduped on `para.strip().lower()`; the
      first-seen original `para.strip()` is kept; `url`/`title` come from
      `sources[0]`.
    - **anything else** (including the default `"concatenate"` and any
      unrecognized string) → `_merge_concatenate` — non-empty `content`
      values are `.strip()`ed and joined with `"\n\n---\n\n"`; `url`/`title`
      come from `sources[0]`.
  - In every branch: `tags` = `sorted({t.lower() for t in all tags if
    isinstance(t, str)})`; `metadata` = `_merge_metadata(sources)`;
    `source_count` = `len(sources)`; `sources` = all URLs in sorted order;
    `merge_strategy` = the **executed** branch name.

#### Private helpers

- `_merge_concatenate(sources) -> MergedContent` — as above; `contents` is
  the list of non-empty stripped bodies, joined with `"\n\n---\n\n"` (empty
  string if no source has content).
- `_merge_longest(sources) -> MergedContent` — `max(sources, key=len(s.content))`.
- `_merge_highest_priority(sources) -> MergedContent` — `sources[0]`.
- `_unique_paragraphs(sources) -> MergedContent` — case/whitespace-insensitive
  paragraph dedup, first-seen original kept.
- `_best_title(sources) -> str` — the longest non-empty title, or `""` if none.
- `_merge_metadata(sources) -> dict[str, Any]` — iterates sources in
  priority-sorted order; a key is set **only if not already present**, so the
  highest-priority source's value wins for any shared key.

## Contract Holes

### 1. `strategy` is never validated — an unrecognized strategy silently runs `concatenate` and `merge_strategy` hides the typo (ARCH-34)

`ContentMerger.__init__(strategy: str = "concatenate")` stores the string
verbatim with **no validation** against the four documented strategies
(`concatenate`, `longest`, `highest_priority`, `unique_paragraphs`). In
`merge()`, the dispatch is an `if/elif/elif/else` chain whose **`else` branch
is the `concatenate` fallback** — so *any* string that is not exactly one of
the three named strategies (e.g. `"longst"`, `"CONCATENATE"`,
`"highest-priority"`, `""`) silently executes `_merge_concatenate`.

The consequence is a two-part silent failure:

- **Wrong behavior, no error**: a caller who misspells a strategy (or passes
  a case-variant) gets concatenated output with no exception, no warning, and
  no way to detect the mistake from the call site.
- **The result field hides the typo**: `MergedContent.merge_strategy` is set
  to the **executed** branch name (`"concatenate"`), **not** the requested
  value. So a caller who asked for `"longst"` reads back
  `merge_strategy == "concatenate"` and has no signal that their requested
  strategy was never honored. The field reports what *happened*, not what was
  *asked for*, so it cannot be used to verify the caller's intent.

This is the single most important hole because it is the only place in the
module where a plausible caller input produces a **silently wrong result with
a self-contradicting field** — every other behavior (empty guard, priority
sort, tag normalization, metadata first-writer-wins) is at least internally
consistent.

**Decision (for the implementer)**: make the strategy contract explicit.
Options:
- **Option A (validate at construction)**: in `__init__`, raise
  `ValueError` for any `strategy` not in the four documented names, and
  reword the `__init__` docstring to state the accepted set. `merge()`'s
  `else` branch then becomes unreachable for a valid instance.
- **Option B (report the requested value)**: keep the lenient fallback but
  set `MergedContent.merge_strategy` to the **requested** `self.strategy`
  (or add a separate field) so a caller can detect that an unrecognized
  strategy fell through to `concatenate`, and reword the `merge` docstring to
  state the fallback explicitly.

Either way the contract must match the code: a caller must not be able to
silently receive concatenated output for a strategy they did not request,
while the result field reports a strategy they did not ask for.

### Secondary observations (not ticketed)

- `merge()` sorts by `priority` descending with a **stable** sort, so equal
  priorities keep their original list order; `sources[0]` (the "primary") is
  therefore the first highest-priority source in input order, not a
  deterministic choice across equal priorities.
- `_merge_metadata` is **first-writer-wins** over the priority-sorted list,
  i.e. highest-priority wins for shared keys — but the docstring says only
  "higher priority wins" without noting that a *lower*-priority source can
  still contribute keys the higher-priority source did not set.
- `unique_paragraphs` splits on the literal `"\n\n"`; single-newline or
  blank-line-variant paragraph breaks are not treated as paragraph
  boundaries, so dedup granularity depends on the source's exact whitespace.
- `source_count` is `len(sources)` (the input length), not the number of
  sources that contributed non-empty content — a source with empty content
  still counts.

## Pinning Tests (for ARCH-34)

- **Unrecognized strategy falls through (the hole)**: construct
  `ContentMerger(strategy="longst")` and call `merge([s1, s2])` where `s1`
  and `s2` have distinct non-empty content. Assert the returned
  `MergedContent.content` equals the `concatenate` output
  (`s1.content.strip() + "\n\n---\n\n" + s2.content.strip()`, in priority
  order) **and** that `merge_strategy == "concatenate"` — pinning that the
  requested `"longst"` was silently replaced by the fallback and that the
  field reports the executed branch, not the requested one.
- **Guard path (empty input)**: `ContentMerger().merge([])` returns `None` —
  pinning the empty-sources guard alongside the strategy-fallback behavior.
