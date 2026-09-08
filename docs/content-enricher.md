# content_enricher — Exact Contract

Module: `personal_index/content_enricher.py` (200 lines)

Enriches indexed content with computed metadata: word/reading metrics,
keywords, content-type flags (code/links/images), a basic sentiment score,
and a text-complexity score. Two public types: `EnrichedContent` (the
result dataclass) and `ContentEnricher` (the enriching engine).

## Public API

### EnrichedContent (dataclass)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| title | str | (required) | Content title, passed through verbatim |
| text | str | (required) | Plain-text body, passed through verbatim |
| word_count | int | `0` | Set by `enrich` to `count_words(text)` |
| reading_time | float | `0.0` | Set by `enrich` to `read_time_minutes(text)` |
| keywords | list[str] | `[]` | Set by `enrich` (see below); `field(default_factory=list)` |
| language | str | `"en"` | **Never computed** by `enrich`; always stays `"en"` |
| has_code | bool | `False` | Set by `enrich` **only when `html` is truthy** |
| has_links | bool | `False` | Set by `enrich` **only when `html` is truthy** |
| has_images | bool | `False` | Set by `enrich` **only when `html` is truthy** |
| sentiment_score | float | `0.0` | Set by `enrich` to `_compute_sentiment(text)`, in `[-1.0, 1.0]` |
| complexity_score | float | `0.0` | Set by `enrich` to `_compute_complexity(text)`, in `[0.0, 1.0]` |
| enriched_at | datetime | `datetime.now(timezone.utc)` | Set at construction; `field(default_factory=...)` |

#### Methods

- `to_dict() -> dict`
  Returns a plain dict of all twelve fields. `enriched_at` is serialized via
  `.isoformat()` (a `str`); every other field is returned as-is. `keywords`
  is the same list object (no copy).

### ContentEnricher

Class-level word lists (shared across all instances, `ClassVar`):

- `POSITIVE_WORDS: ClassVar[set[str]]` — a fixed set of positive sentiment
  words (`"good"`, `"great"`, `"excellent"`, … `"improve"`).
- `NEGATIVE_WORDS: ClassVar[set[str]]` — a fixed set of negative sentiment
  words (`"bad"`, `"terrible"`, `"awful"`, … `"drawback"`).

Both are matched by **set intersection against distinct tokens** (see
`_compute_sentiment`), so a word's *frequency* is ignored — only its
presence matters.

- `__init__(self, top_n_keywords: int = 10)`
  Stores `self.top_n_keywords`. This is the `top_n` passed to
  `extract_keywords` in `enrich`. `min_freq` is **hardcoded to `1`** and is
  not configurable.

- `enrich(self, title: str, text: str, html: str | None = None) -> EnrichedContent`
  Builds an `EnrichedContent(title=title, text=text)` and sets:
  - `word_count = count_words(text)`
  - `reading_time = read_time_minutes(text)`
  - `keywords = [kw[0] for kw in extract_keywords(text, top_n=self.top_n_keywords, min_freq=1)]`
    (each `extract_keywords` result is a `(word, freq)` tuple; only `word`
    is kept, in the order `extract_keywords` returns them)
  - `has_code` / `has_links` / `has_images` — set **only when `html` is
    truthy** (via `_detect_code` / `_detect_links` / `_detect_images`);
    when `html` is `None` or empty they are left at the dataclass default
    `False`
  - `sentiment_score = _compute_sentiment(text)`
  - `complexity_score = _compute_complexity(text)`
  - `language` is **never** touched — it stays `"en"`.
  Returns the populated `EnrichedContent`.

- `batch_enrich(self, items: list[tuple[str, str]]) -> list[EnrichedContent]`
  Returns `[self.enrich(title, text) for title, text in items]`. Each item is
  a `(title, text)` tuple; **`html` is never passed**, so every returned
  `EnrichedContent` has `has_code`/`has_links`/`has_images` = `False`
  (see Contract Hole 1).

#### Private helpers

- `_detect_code(self, html: str) -> bool`
  `True` iff `html` matches any of `<pre…>…</pre>`, `<code…>…</code>`,
  `<script…>…</script>` (regex, `re.DOTALL | re.IGNORECASE`).

- `_detect_links(self, html: str) -> bool`
  `True` iff `html` matches `<a\s+[^>]*href=` (regex, `re.IGNORECASE`).

- `_detect_images(self, html: str) -> bool`
  `True` iff `html` matches `<img\s+[^>]*src=` (regex, `re.IGNORECASE`).

- `_compute_sentiment(self, text: str) -> float`
  `words = set(tokenize(text))`; `pos = len(words & POSITIVE_WORDS)`;
  `neg = len(words & NEGATIVE_WORDS)`; `total = pos + neg`. If `total == 0`
  returns `0.0`; else returns `(pos - neg) / total`. Range `[-1.0, 1.0]`.
  Because the input is a **set**, a word repeated N times counts once.

- `_compute_complexity(self, text: str) -> float`
  `tokens = tokenize(text)`; if empty returns `0.0`. Otherwise
  `avg_length = sum(len(t) for t in tokens) / len(tokens)`;
  `length_score = min(avg_length / 15.0, 1.0)`;
  `unique_ratio = len(set(tokens)) / len(tokens)`;
  returns `round(length_score * 0.4 + unique_ratio * 0.6, 4)`.
  Range `[0.0, 1.0]`.

## Contract Holes

### 1. `batch_enrich` cannot enrich HTML — content-type flags are silently always-False (ARCH-33)

`enrich()` accepts an optional `html` argument and, when it is truthy, sets
`has_code` / `has_links` / `has_images` from `_detect_code` /
`_detect_links` / `_detect_images`. `batch_enrich(items: list[tuple[str, str]])`
accepts **only `(title, text)` tuples** and calls `self.enrich(title, text)`
with **no `html` argument**. The consequence:

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

**Decision (for the implementer)**: make the two entry points consistent.
Options:
- **Option A (extend the batch signature)**: change `batch_enrich` to accept
  `list[tuple[str, str, str | None]]` (or a list of `EnrichedContent`-shaped
  inputs) so each item can carry `html`, and pass it through to `enrich`.
  Update the docstring to state the tuple arity.
- **Option B (document the limitation)**: keep the `(title, text)` signature
  but reword the `batch_enrich` docstring to state explicitly that HTML-based
  content-type detection is **not** performed in batch mode and that
  `has_code`/`has_links`/`has_images` are always `False` there.

Either way the contract must match the code: a caller must not be able to
silently receive all-False content-type flags from a path that looks
equivalent to `enrich`.

### Secondary observations (not ticketed)

- `language` is never computed; it is always the dataclass default `"en"`.
  This is stated in the `enrich` docstring, so it is a known limitation, not
  a hidden hole — but any consumer that reads `language` as a real
  classification will get a constant.
- `_compute_sentiment` operates on `set(tokenize(text))`, so word
  **frequency is ignored**: `"good good good good"` scores the same as
  `"good"`. This is a deliberate simplicity choice, not a bug, but it means
  the score is a presence-based signal, not a weighted one.
- `enrich` hardcodes `min_freq=1` for `extract_keywords`; only `top_n` is
  configurable via `__init__`.

## Pinning Tests (for ARCH-33)

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
