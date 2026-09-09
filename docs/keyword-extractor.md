# keyword-extractor — `personal_index.keyword_extractor`

Keyword extraction from text using frequency analysis. Tokenizes text (via
`personal_index.text_utils.tokenize` with `remove_stopwords=True`), drops
tokens shorter than `min_length`, counts frequencies, scores each keyword as
`frequency * log(1 + frequency)` (emphasizing repeats), and returns the top
keywords by score. Also supports n-gram phrase extraction, per-term
frequencies, and cross-text keyword comparison.

Stdlib-only (`math`, `collections.Counter`, `dataclasses`) plus the
`personal_index.text_utils.tokenize` helper. No I/O, no network, no disk —
every method is a pure in-memory transform over the input string.

## Public API

### `Keyword` (dataclass)

One extracted keyword with its frequency, score, and positions.

| Field | Type | Default |
|-------|------|---------|
| `text` | `str` | — |
| `frequency` | `int` | — |
| `score` | `float` | — |
| `positions` | `list[int] \| None` | `None` |

- `__post_init__` — if `positions is None`, sets `positions = []`. So after
  construction `positions` is **always** a `list[int]` (the `None` default is
  only the pre-normalization sentinel; a hand-built `Keyword(positions=None)`
  is rewritten to `[]`). `positions` holds the **token indices** (0-based, in
  the post-stopword-removal, post-`min_length`-filter token stream) at which
  the keyword occurs.

### `KeywordExtractor`

`__init__(self, min_length: int = 3, max_keywords: int = 20,
min_frequency: int = 1)` — stores the three thresholds as instance attributes.
`min_length` is the minimum token length kept; `max_keywords` is the cap on
how many keywords `extract` / `extract_phrases` return; `min_frequency` is the
minimum occurrence count for a token to be kept (default `1` = keep every
token that survives the length filter).

All methods call `tokenize(text, remove_stopwords=True)` and then filter to
`len(token) >= min_length`.

#### `extract(text: str) -> list[Keyword]`

- **Guard:** `text` falsy → `[]`; no tokens survive the length filter → `[]`.
- Counts tokens with `Counter`, keeps those with `count >= min_frequency`.
- Records each keyword's `positions` (token indices in the filtered stream).
- Scores each as `count * math.log(1 + count)`.
- Sorts by `score` **descending** and returns `keywords[: self.max_keywords]`.

> The return is **capped at `self.max_keywords`** (default 20), independent of
> any caller request. See Contract Holes for how this cap leaks into
> `extract_top_n`.

#### `extract_phrases(text: str, n: int = 2) -> list[tuple[str, int]]`

- **Guard:** `text` falsy → `[]`; fewer than `n` tokens survive the length
  filter → `[]`.
- Builds every contiguous `n`-gram of the filtered token stream
  (`" ".join(tokens[i:i+n])` for `i` in `range(len(tokens) - n + 1)`), counts
  them, and returns `Counter.most_common(self.max_keywords)` — a list of
  `(phrase, count)` tuples, most frequent first, capped at `max_keywords`.

#### `extract_top_n(text: str, n: int = 10) -> list[str]`

- **Guard:** `n <= 0` → `[]`.
- Returns `[kw.text for kw in self.extract(text)[:n]]` — the top `n` keyword
  strings by score.

> **`n` is silently capped by `self.max_keywords`.** Because `extract` already
> truncates to `self.max_keywords` (default 20) before this slice, requesting
> `n > max_keywords` returns only `max_keywords` items, not `n`. See Contract
> Holes.

#### `compute_term_frequency(text: str) -> dict[str, float]`

- **Guard:** no tokens survive the length filter → `{}`.
- Returns `{word: count / total}` where `total = len(filtered tokens)` — the
  raw (un-normalized-by-document-length) term frequency of each surviving
  token. Note: this does **not** apply the `min_frequency` filter and does
  **not** cap the result; it returns one entry per distinct surviving token.

#### `compare_keywords(text1: str, text2: str) -> dict[str, float]`

- Extracts keywords from both texts (each capped at `self.max_keywords`),
  intersects the keyword sets, and for each shared keyword returns the
  **mean** of the two scores: `(score1 + score2) / 2`.
- Returns a dict sorted by the mean score **descending**.
- **Guard:** disjoint keyword sets → `{}`.

> Shares the `extract` cap: a keyword that is present in both texts but ranks
> beyond `max_keywords` in either is dropped from the intersection. See
> Contract Holes (secondary).

### `extract_keywords(text: str, max_keywords: int = 10) -> list[str]` (module fn)

Convenience wrapper used by `pipeline_runner`. Constructs
`KeywordExtractor(max_keywords=max_keywords)` and returns
`extractor.extract_top_n(text, n=max_keywords)`. Because it passes the same
value to both the constructor cap and `n`, the cap never binds here — it
returns up to `max_keywords` keywords.

## Contract Holes

**Single most important hole — `extract_top_n`'s `n` is silently capped by the
constructor's `max_keywords`.** `extract_top_n(text, n)` is documented as
"Extract top N keywords," but it delegates to `extract(text)`, which already
truncates its result to `self.max_keywords` (default **20**) *before*
`extract_top_n` slices to `n`. So whenever `n > max_keywords`, the caller
silently receives `max_keywords` items instead of `n`. Empirically: on text
with 40 distinct keywords, `KeywordExtractor().extract_top_n(text, n=50)`
returns **20**, not 50. The `n` parameter over-promises; the true cap is an
invisible constructor argument the caller did not ask about. This is a
silent-wrong-result hole (the ARCH-2 umbrella class): no exception, no
warning, just fewer keywords than requested. See `tickets/ARCH-57.md`.

Secondary (documented here, not ticketed): `compare_keywords` shares the same
root cause — it intersects the two `extract` results, each already truncated
to `max_keywords`, so a keyword present in both texts but ranking beyond
`max_keywords` in either is silently excluded from the comparison.
