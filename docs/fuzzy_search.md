# Fuzzy Search — `personal_index.fuzzy_search`

Spec for the `personal_index/fuzzy_search.py` module (251 lines). A live
production module: dedicated `tests/test_fuzzy_search.py` +
`tests/deep/test_fuzzy_search_adversarial.py` both import from it.

> **Near-name note:** this page documents the underscore module
> `personal_index/fuzzy_search.py` (the `FuzzySearcher` class + the
> module-level `levenshtein_distance` / `levenshtein_similarity` functions).
> It is NOT a sibling subpackage and has no hyphen-named doc collision; the
> index entry here is the only `fuzzy_search` page.

## Public API

### `class FuzzyMatch` (dataclass, line 10)
- Fields: `text: str`, `score: float`, `matched_indices: list[int]`
  (default `[]` via `field(default_factory=list)`).
- `__post_init__` (line 16): if `matched_indices is None`, resets it to `[]`
  (defensive; the default factory already yields `[]`).

### Module functions
- `levenshtein_distance(s1: str, s2: str) -> int` (line 21) — Wagner-Fischer
  edit distance, O(min(len(s1), len(s2))) space. Guard paths: `s1 == s2` →
  `0`; `not s1` → `len(s2)`; `not s2` → `len(s1)`. Swaps so `s1` is the
  shorter string for memory efficiency.
- `levenshtein_similarity(s1: str, s2: str) -> float` (line 54) —
  `1.0 - distance / max(len(s1), len(s2))`. Guard paths: both empty → `1.0`;
  exactly one empty → `0.0`. Returns in `[0.0, 1.0]`.

### `class FuzzySearcher` (line 69)
- `__init__(self, min_score: float = 0.4)` (line 72) — stores the threshold.
- `search(self, query: str, texts: list[str]) -> list[FuzzyMatch]` (line 75)
  — guard: `not query or not texts` → `[]`. For each text, scores
  `_compute_score(query.lower(), text.lower())`; keeps it iff
  `score >= self.min_score` (boundary is `>=`, inclusive). Computes
  `matched_indices` via `_find_match_indices` on the lowercased pair. Sorts
  results by `score` descending.
- `search_in_dict(self, query: str, items: dict[str, str]) -> list[FuzzyMatch]`
  (line 96) — searches keys + values, dedupes by value (a key equal to a value
  is scored once). Same `>= min_score` filter and descending sort. Note: no
  `not query` guard here — an empty query scores every entry at `0.0`
  (`_compute_score` returns `0.0` for empty query) and returns `[]` only
  because `0.0 < min_score` for the default threshold; with `min_score=0.0`
  it would return every entry.
- `_compute_score(self, query: str, text: str) -> float` (line 118) —
  private, contract-relevant. Guard: `not query or not text` → `0.0`.
  Cascade: exact match → `1.0`; `query in text` (substring) → `0.9`;
  `_char_match_score` (ordered subsequence) → `0.85` if all query chars
  appear in order, else `0.0`; else `max(levenshtein_similarity,
  SequenceMatcher.ratio())`, boosted to `>= 0.7` if `text` starts with the
  first half of `query`.
- `_char_match_score(self, query: str, text: str) -> float` (line 151) —
  returns `0.85` iff every query char appears in `text` in order (and
  `len(query) <= len(text)`), else `0.0`.
- `_find_match_indices(self, query: str, text: str) -> list[int]` (line 176)
  — returns the index range to highlight. Three branches: (a) `query in text`
  → contiguous range at `text.index(query)`; (b) `len(query) > len(text)` →
  best window of `query` of length `len(text)`, returns `range(len(text))`
  iff best ratio `> 0.5`; (c) else best substring of `text` of length
  `len(query)`, returns `range(best_start, best_start+len(query))` iff best
  ratio `> 0.5`. Returns `[]` when no branch exceeds the `0.5` threshold.
  All returned indices are valid positions in `text` (in-range, non-overlapping
  contiguous runs), so `highlight`/`highlight_html` slicing is safe.
- `highlight(self, text: str, indices: list[int]) -> str` (line 212) — plain
  text: wraps each char at an index in `\033[1m...\033[0m` (ANSI bold).
  `not indices` → returns `text` unchanged.
- `highlight_html(self, text: str, indices: list[int]) -> str` (line 226) —
  HTML: wraps each char at an index in `<mark>...</mark>`. `not indices` →
  returns `text` unchanged. **See Contract Hole 1: the non-indexed chars are
  inserted raw, with no HTML entity escaping.**
- `search_with_highlight(self, query: str, texts: list[str],
  html: bool = False) -> list[tuple[FuzzyMatch, str]]` (line 240) — runs
  `search`, then pairs each match with `highlight_html` (if `html`) or
  `highlight` (else) of its `matched_indices`.

## Contract Hole 1 — `highlight_html` does not HTML-escape the text (XSS class)

`highlight_html` (line 226) builds its output by appending each character of
`text` **raw** — either wrapped in `<mark>...</mark>` (indexed chars) or
appended as-is (non-indexed chars):

    for i, char in enumerate(text):
        if i in idx_set:
            result.append(f"<mark>{char}</mark>")
        else:
            result.append(char)          # line 237: raw, unescaped

Neither branch escapes HTML entities. So any `<`, `>`, `&`, `"`, `'` in the
searched text passes straight through into the returned HTML. A text such as
`<script>alert(1)</script>` (or a title containing `&` / `"` / `<`) is emitted
verbatim, so embedding the result in a page yields **unescaped, executable /
malformed markup** — the classic XSS / markup-injection class. The plain
`highlight` path is unaffected (it emits ANSI codes, not HTML), which makes
the HTML path the single unguarded sink.

The docstring (`"Create HTML-highlighted version of text."`) omits the
escaping behavior entirely, so a caller reading the contract has no reason to
expect the returned string to be safe to embed. This is the same
"advertised safety not actually provided" class as ARCH-39/40/41/42/44/46
(silent unsafe output on a public path), and it is the single most important
hole in this module because the output is user-facing markup.

**Recommended contract (for the implementer):** escape the text before
wrapping — apply `html.escape` (or an equivalent entity-escaping of
`&`, `<`, `>`, `"`, `'`) to each character / the whole text so the returned
string is safe to embed, while still wrapping the matched indices in
`<mark>...</mark>`. The plain `highlight` path must remain unchanged (ANSI,
no escaping).

## Secondary notes (not ticketed)
- `search_in_dict` has no explicit `not query` guard (unlike `search`); an
  empty query returns `[]` only via the `min_score` filter, not via an early
  return. Behavior is correct at the default threshold but the guard is
  implicit rather than stated.
- `_find_match_indices` returns `[]` (not an error) when no branch exceeds the
  `0.5` ratio threshold, so a match can carry `matched_indices == []` and
  `highlight`/`highlight_html` then return the text unchanged — a valid,
  documented-by-code path, not a defect.
