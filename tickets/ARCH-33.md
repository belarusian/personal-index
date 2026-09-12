# ARCH-33: content_enricher — `batch_enrich` cannot pass HTML, so content-type flags are silently always-False

Status: IMPLEMENTED #1286@fb78626
Component: `personal_index/content_enricher.py`
Issue: #1093
Refs: ARCH-2 (#983 umbrella)

## Symptom

`ContentEnricher.enrich(title, text, html=None)` accepts an optional `html`
argument and, when it is truthy, sets `has_code` / `has_links` / `has_images`
from `_detect_code` / `_detect_links` / `_detect_images`. But
`ContentEnricher.batch_enrich(items: list[tuple[str, str]])` accepts **only
`(title, text)` tuples** and calls `self.enrich(title, text)` with **no
`html` argument**. The consequence:

- Every `EnrichedContent` produced by `batch_enrich` has
  `has_code == has_links == has_images == False`, **regardless of the actual
  content** — even when the source page is full of code blocks, links, and
  images.
- There is **no error, no warning, and no way to pass HTML** through the
  batch path. A caller doing a bulk import via `batch_enrich` gets
  content-type flags that are all `False` with no signal that the flags are
  meaningless.
- This is an **inconsistency between the two public entry points**: the same
  `(title, text, html)` content yields different `has_*` flags depending on
  whether it is enriched via `enrich` (with `html`) or `batch_enrich`
  (without). The batch path is a strict, silent subset of the single path.

## Evidence

- `personal_index/content_enricher.py` line 79:
  `def enrich(self, title: str, text: str, html: str | None = None) -> EnrichedContent:`
- `personal_index/content_enricher.py` lines 124-127: the `if html:` block
  that sets `has_code` / `has_links` / `has_images` (skipped when `html` is
  falsy).
- `personal_index/content_enricher.py` line 191:
  `def batch_enrich(self, items: list[tuple[str, str]]) -> list[EnrichedContent]:`
- `personal_index/content_enricher.py` line 199:
  `return [self.enrich(title, text) for title, text in items]` — no `html`
  argument is ever passed.
- `EnrichedContent` dataclass defaults (lines 27-29): `has_code` / `has_links`
  / `has_images` all default to `False`.

## Minimal additive fix

Pick ONE of the two, and make the two entry points consistent:

**Option A (extend the batch signature)**: change `batch_enrich` to accept
`list[tuple[str, str, str | None]]` (or a list of `EnrichedContent`-shaped
inputs) so each item can carry `html`, and pass it through to `enrich`.
Update the `batch_enrich` docstring to state the tuple arity.

**Option B (document the limitation)**: keep the `(title, text)` signature
but reword the `batch_enrich` docstring to state explicitly that HTML-based
content-type detection is **not** performed in batch mode and that
`has_code`/`has_links`/`has_images` are always `False` there.

The contract decision is: a caller must not be able to silently receive
all-False content-type flags from a path that looks equivalent to `enrich`.
Option A is preferred if batch enrichment is meant to be a drop-in for
`enrich`; Option B if the batch path is intentionally text-only.

## Acceptance criteria

1. The `batch_enrich` contract matches its code: either it can pass `html`
   through to `enrich` (Option A) or its docstring explicitly states that
   content-type flags are always `False` in batch mode (Option B).
2. If Option A: a test below (batch vs single consistency) passes with both
   paths producing the same `has_*` flags for the same `(title, text, html)`.
3. If Option B: a docstring-assertion test pins the corrected "no HTML /
   flags always False" wording against the `batch_enrich` method object.
4. No behavior change to the single `enrich` contract (see
   `docs/content-enricher.md`).

## Pinning tests to add

- **Batch vs single consistency (the hole)**: for a `(title, text, html)`
  where `html` contains a `<pre>` block, an `<a href=…>` link, and an
  `<img src=…>` image, assert that `enrich(title, text, html)` yields
  `has_code == has_links == has_images == True`, while
  `batch_enrich([(title, text)])` yields all three `False` — pinning the
  current silent divergence (or, after the fix, that both paths agree).
- **`enrich` guard path (no html)**: `enrich(title, text)` with `html=None`
  leaves `has_code`/`has_links`/`has_images` at `False` (the default), while
  still populating `word_count`, `reading_time`, `keywords`,
  `sentiment_score`, and `complexity_score`.
- **`enrich` with html**: the three flags are set from the detectors (a
  `<pre>`-only html → `has_code True`, `has_links`/`has_images` False).
- **`to_dict`**: `enriched_at` is a `str` (ISO-8601) and all twelve keys are
  present.

## Docs update (same PR)

`docs/content-enricher.md` (new) documents the full public API and lists this
as Contract Hole 1; `docs/README.md` gains the content-enricher index line
under "Core subsystems".
