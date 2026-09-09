# text-utils — `personal_index.text_utils`

Pure text-processing helpers used across the pipeline: whitespace/HTML
normalization, truncation, sentence/paragraph splitting, word frequency and
keyword extraction, string distance/similarity, slugification, search-term
highlighting, word/character counting, reading-time estimation, and tokenizing.

Stdlib-only (`re`, `unicodedata`, `collections.Counter`). Every helper is a
**pure function** — no I/O, no mutation of inputs, no module state except the
read-only `STOPWORDS` set. Every helper guards the empty/falsy input up front
and returns an empty value (`""`, `[]`, `{}`, `0`) rather than raising.

## Public API

### `normalize_whitespace(text: str) -> str`

Collapse every whitespace run into a single space and strip the ends.

- Guard: `text` falsy → `""`.
- Otherwise `re.sub(r"\s+", " ", text).strip()`.

### `remove_html_tags(html: str) -> str`

Strip HTML tags, preserving the text content.

- Guard: `html` falsy → `""`.
- Removes `<script>…</script>` and `<style>…</style>` blocks (DOTALL,
  case-insensitive) **before** removing all remaining `<…>` tags.
- Decodes a fixed set of entities: `&nbsp;`→space, `&amp;`→`&`, `&lt;`→`<`,
  `&gt;`→`>`, `&quot;`→`"`, `&#39;`→`'`. (Other entities are left as-is.)
- Returns `normalize_whitespace(text)` of the result.

### `truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str`

Truncate to at most `max_length` characters, preferring a word boundary.

- Guard: `text` falsy → `""`; `len(text) <= max_length` → `text` unchanged.
- Cuts at the last space **only if** that space is after `60%` of
  `max_length`; otherwise it cuts at exactly `max_length` and **may break a
  word**. `suffix` is appended only when truncation occurs.

### `extract_sentences(text: str, min_length: int = 10) -> list[str]`

Split on sentence-ending punctuation (`(?<=[.!?])\s+`), keeping sentences of
length `>= min_length`.

- Guard: `text` falsy → `[]`.

### `extract_paragraphs(text: str, min_length: int = 20) -> list[str]`

Split on blank-line runs (`\n\s*\n`), keeping paragraphs of length
`>= min_length`.

- Guard: `text` falsy → `[]`.

### `word_frequency(text: str, min_freq: int = 1, stop_words: set[str] | None = None) -> dict[str, int]`

Word → count for alphabetic words (`\b[a-zA-Z]+\b`, lowercased).

- Guard: `text` falsy → `{}`.
- `stop_words` (optional set) is subtracted before counting; only words with
  count `>= min_freq` are returned.

### `extract_keywords(text: str, top_n: int = 10, min_freq: int = 2) -> list[tuple[str, int]]`

Top keywords by frequency, as `(word, count)` tuples sorted descending.

- Guard: `top_n <= 0` → `[]`.
- Seeds from `word_frequency(text, min_freq=min_freq)`; if that yields fewer
  than `top_n`, it back-fills from `word_frequency(text, min_freq=1)` (excluding
  words already present) until `top_n` is reached. Returns at most `top_n`.

### `levenshtein_distance(s1: str, s2: str) -> int`

Edit distance (insertions/deletions/substitutions) between two strings.

- Swaps so `s1` is the longer string; `s2` empty → `len(s1)`.
- Two-row DP; returns the final cell.

### `similarity_ratio(s1: str, s2: str) -> float`

Similarity in `[0.0, 1.0]` = `1.0 - distance / max(len(s1), len(s2))`.

- Both empty → `1.0`; exactly one empty → `0.0`.

### `slugify(text: str) -> str`

URL-friendly slug.

- Guard: `text` falsy → `""`.
- NFKD-normalizes, drops non-ASCII, lowercases, strips non-word chars,
  collapses runs of whitespace/`_`/`-` into a single `-`, strips leading/trailing
  `-`.

### `highlight_text(text: str, terms: list[str], tag: str = "mark") -> str`

Wrap case-insensitive matches of `terms` in `<tag>…</tag>`.

- Guard: `text` falsy or `terms` empty → `text` unchanged.
- Filters out falsy terms; if none remain → `text` unchanged.
- Single-pass regex alternation, **longest-first**, so each source position is
  matched at most once and shorter terms are not re-matched inside markers
  inserted for longer terms. The original-cased term is used in the marker.

### `count_words(text: str) -> int`

`len(text.split())`. Guard: `text` falsy → `0`.

### `count_characters(text: str, include_spaces: bool = True) -> int`

Character count. Guard: `text` falsy → `0`. With `include_spaces=False`,
whitespace is removed first (`re.sub(r"\s+", "", text)`).

### `read_time_minutes(text: str, wpm: int = 200) -> int`

Estimated reading time in whole minutes.

- `words = count_words(text)`; returns `max(1, round(words / wpm))`.
- **Precondition (currently unenforced):** `wpm` must be a **positive integer**
  (`wpm > 0`). The body performs a raw `words / wpm` division with **no guard on
  `wpm`**, so `wpm == 0` raises `ZeroDivisionError` and `wpm < 0` silently
  returns `1` (the negative quotient is clamped by `max(1, …)`). See the
  Contract Holes section and ARCH-60.
- Documented minimum is `1`: non-empty text at `wpm=200` returns `>= 1`, and
  empty text returns `1`.

### `tokenize(text: str, lowercase: bool = True, remove_stopwords: bool = False) -> list[str]`

Tokenize into words.

- Guard: `text` falsy → `[]`.
- Matches `\b[a-zA-Z][a-zA-Z0-9_-]*\b|\b\d+\b` (letter-led words and bare
  numbers). `lowercase` lowercases each token; `remove_stopwords` drops tokens in
  the module-level `STOPWORDS` set.

## Contract Holes

- **`read_time_minutes` has no guard on `wpm` (ARCH-60).**
  The body is `max(1, round(words / wpm))` with a raw division and **no
  precondition check on `wpm`**. Two distinct failures:
  - `wpm == 0` → `ZeroDivisionError: division by zero` (verified:
    `read_time_minutes('word '*300, wpm=0)` raises).
  - `wpm < 0` → **silently returns `1`** (verified:
    `read_time_minutes('word '*300, wpm=-5)` returns `1`), because the negative
    quotient is clamped by `max(1, …)`. A negative reading speed is accepted and
    produces a bogus "1 minute" answer instead of being rejected.
  The docstring says "minimum 1" but never states the `wpm > 0` precondition, so
  a caller cannot tell that `wpm` must be a positive integer. This is the same
  unvalidated-numeric-input class as the `throttle` / `rate_limiter`
  ZeroDivisionError holes (ARCH-59 / ARCH-37). ARCH-60 picks ONE resolution
  (reject `wpm <= 0` up front with `ValueError`, or clamp `wpm` to a positive
  floor) and pins it.
