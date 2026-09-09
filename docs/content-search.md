# Content search (`personal_index.content_search`)

Status: **spec** — audited against current code (cycle 216).

Full-text search over in-memory items: an inverted index with three ranking
modes (`tf`, `tfidf`, `bm25`), field filters, snippet extraction/highlighting,
autocomplete suggestions, and JSON persistence. Stdlib-only (`math`, `re`,
`string`, `dataclasses`, `typing`).

## Snippet
`@dataclass` with fields: `text: str`, `highlighted: str`,
`start_offset: int = 0`, `end_offset: int = 0`,
`matched_terms: list[str] = field(default_factory=list)`.

- `to_dict() -> dict[str, Any]` — returns a NEW dict with exactly five keys:
  `text`, `highlighted`, `start_offset`, `end_offset`, `matched_terms`
  (passed through by reference, NOT copied). No guard path; no side effects.

## SnippetExtractor
`SnippetExtractor(max_snippet_length: int = 200, max_snippets: int = 3,
ellipsis: str = "...", marker_open: str = "<mark>", marker_close: str =
"</mark>")`.

- `extract(text: str, query_terms: list[str]) -> list[Snippet]` —
  **Guard path:** if `text` is empty/falsy OR `query_terms` is an empty list,
  returns `[]` (no snippet). **No-match fallback:** if no query term is found
  anywhere in `text`, returns a single `Snippet` from `_make_fallback_snippet`
  (the leading portion of `text`, ellipsis-suffixed when truncated past
  `max_snippet_length`). **Match case:** every occurrence of each query term is
  located (case-insensitive, overlapping matches via `start = pos + 1`), the
  positions are grouped into windows by `_group_into_windows`, and each window
  becomes a `Snippet` via `_make_snippet` carrying `text`, `highlighted`
  (terms wrapped in `marker_open`/`marker_close`), `start_offset`,
  `end_offset`, and `matched_terms` (deduped, order-preserving). The returned
  list is truncated to `max_snippets` (default 3).
- `highlight_text(text: str, terms: list[str]) -> str` — wraps every
  occurrence of each term in `marker_open`/`marker_close` (case-insensitive,
  longest-term-first to avoid partial replacements) WITHOUT snippet
  extraction/windowing. No guard path: with no terms it returns `text`
  unchanged.

### Private helpers (documented for the snippet contract)
- `_group_into_windows(text, positions) -> list[Snippet]` — groups match
  positions into windows; two positions are in the same group while
  `pos[0] - current_group[-1][0] <= max_snippet_length` (note: the gap is
  measured against `max_snippet_length`, NOT the half-window). Returns `[]`
  when `positions` is empty.
- `_make_snippet(text, positions, half_window) -> Snippet | None` — builds one
  `Snippet` from a group; the window is `[window_start, window_end]` from
  `_calc_window`, `highlighted` is prefixed with `ellipsis` when
  `window_start > 0` and suffixed when `window_end < len(text)`.
- `_calc_window(text, first_start, last_end, half) -> tuple[int, int]`
  (`@staticmethod`) — window is `[max(0, first_start - half),
  min(len(text), last_end + half)]`, then snapped to the nearest word boundary
  (previous space for the start, next space for the end) when not at an edge.
- `_highlight_terms(text, terms) -> str` — case-insensitive regex
  substitution, terms sorted longest-first; returns `text` unchanged when
  `terms` is empty.
- `_make_fallback_snippet(text) -> list[Snippet]` — single-element list; the
  whole `text` when `len(text) <= max_snippet_length`, else the leading
  `max_snippet_length` chars broken at the last space (only when that space is
  past `max_snippet_length * 0.5`), ellipsis-suffixed.

## SearchIndex
`SearchIndex()` — in-memory inverted index. Internal state:
`_index: dict[str, set]` (term -> set of item_ids),
`_items: dict[str, dict[str, Any]]` (id -> item),
`_term_freq: dict[str, dict[str, int]]` (term -> {item_id: count}),
`_doc_lengths: dict[str, int]` (item_id -> total token count), and a default
`_snippet_extractor = SnippetExtractor()`.

- `add_item(item: dict[str, Any]) -> None` — stores the item under
  `str(item.get("id", id(item)))` (a missing/`None` id falls back to the
  object's `id()`), extracts text via `_extract_text`, tokenizes via
  `_tokenize`, records the doc length, and updates `_index` / `_term_freq`.
  Re-adding the same id overwrites the stored item but does NOT remove the
  old tokens first (see Contract holes).
- `add_items(items: list[dict[str, Any]]) -> None` — calls `add_item` per item.
- `remove_item(item_id: str) -> None` — **Guard path:** `str(item_id)`; if the
  id is not in `_items`, returns immediately (no-op). Otherwise pops the item,
  re-derives its tokens, and discards the id from every `_index` /
  `_term_freq` entry (deleting the entry when it becomes empty), then pops
  `_doc_lengths`.
- `search(query: str, filters: dict[str, Any] | None = None, limit: int = 20,
  offset: int = 0, ranking: str = "tf", highlight: bool = False) ->
  dict[str, Any]` — tokenizes the query (lowercase, punctuation stripped,
  stop-words and single characters dropped). **Guard path:** if no tokens
  remain, returns exactly `{"results": [], "total": 0, "query": query}`
  without touching the index. Otherwise finds candidate items
  (`_find_candidates`), scores them with the requested ranking (`"tf"` default
  = summed term frequency, `"tfidf"`, or `"bm25"`; any other value falls
  through to the `"tf"` branch), optionally narrows them with `filters`
  (`_apply_filters`), sorts by score descending, and returns a dict with:
  - `"results"`: the `offset:offset+limit` page of entries, each a dict with
    `"item"` (the stored item with its `"content"` key removed) and `"score"`
    (rounded to 4 decimals); when `highlight=True` each entry also carries
    `"snippets"` (list of `Snippet.to_dict()` dicts built from
    `item["content"]` or `item["description"]`), and the key is ABSENT when
    `highlight=False`.
  - `"total"`: `len(ranked)` = the count of ALL ranked candidates BEFORE the
    offset/limit page slice, so it can exceed `len(results)`.
  - `"query"`: the original query string, echoed back unchanged.
- `item_count` (property) -> `int` — `len(self._items)`.
- `term_count` (property) -> `int` — `len(self._index)`.
- `get_suggestions(prefix: str, limit: int = 5) -> list[str]` — **Guard
  path:** if `limit <= 0`, returns `[]`. Otherwise returns the sorted index
  terms that `startswith(prefix.lower())`, truncated to `limit`.
- `save_index(filepath) -> None` — writes a JSON object with keys `items`,
  `index` (each term's set serialized as a list), `term_freq`, `doc_lengths`;
  `default=str` for non-JSON-serializable values.
- `load_index(filepath) -> None` — **Guard paths:** on `JSONDecodeError` or a
  non-dict payload, returns without mutating state. Otherwise replaces
  `_items`, `_index` (lists re-set-ified), `_term_freq`, and `_doc_lengths`
  (defaulting to `{}`); when `_doc_lengths` is empty it is re-derived from the
  loaded items via `_extract_text` / `_tokenize`.
- `highlight_matches(text, query, marker: str = "*") -> str` — tokenizes
  `query` and wraps each token present in `text` (case-insensitive) in
  `marker`...`marker`. Distinct from `SnippetExtractor.highlight_text`: this
  uses the `*` marker and per-token substitution, not the `<mark>` markers.

### Private helpers (documented for the ranking/filter contract)
- `_find_candidates(tokens) -> dict[str, float]` — union of the item_ids in
  the index for each token, each seeded at `0.0`.
- `_score_candidates(cands, tokens, ranking) -> dict[str, float]` — dispatches
  to `_score_tfidf` / `_score_bm25` / the default summed-term-frequency loop.
- `_score_tfidf(candidates, query_tokens) -> dict[str, float]` —
  `idf = log(n_docs / max(df, 1))`, `tf` normalized by doc length
  (`tf / max(doc_len, 1)`), summed per candidate.
- `_score_bm25(candidates, query_tokens, k1: float = 1.5, b: float = 0.75) ->
  dict[str, float]` — standard BM25 with
  `idf = log((n_docs - df + 0.5) / (df + 0.5) + 1.0)` and
  `avgdl = sum(doc_lengths) / n_docs` (or `1.0` when empty).
- `_apply_filters(candidates, filters) -> dict[str, float]` — keeps a
  candidate only when `_matches_filters` is true for its stored item.
- `_matches_filters(item, filters) -> bool` — per key: a list/set value means
  "item value intersects the set" (or "item value is in the list" when the
  item value is not a list/set); a dict value supports `$gte` / `$lte`
  (skipped when the item value is `None`); any other value means exact
  `==`. All keys must pass.
- `_extract_text(item) -> str` — joins the string parts of `title`,
  `description`, `content`, `tags` (a list contributes each element's `str` or
  `.name` attribute) with single spaces.
- `_tokenize(text) -> list[str]` — lowercase, strip punctuation, split on
  whitespace, drop stop-words and tokens of length `<= 1`.

## ContentSearch
`ContentSearch()` — high-level facade holding `self.index = SearchIndex()`.

- `index_items(items: list[dict[str, Any]]) -> None` — delegates to
  `self.index.add_items`.
- `search(query, filters=None, limit=20, offset=0, ranking="tf",
  highlight=False) -> dict[str, Any]` — delegates to `self.index.search` with
  the same arguments and returns its result unchanged.
- `remove_item(item_id: str) -> None` — delegates to `self.index.remove_item`.
- `get_suggestions(prefix, limit=5) -> list[str]` — delegates to
  `self.index.get_suggestions`.

## Contract holes
- **`add_item` does not remove the old tokens on a re-add.** `add_item`
  overwrites `self._items[item_id]` but never discards the id from the
  `_index` / `_term_freq` entries that the PREVIOUS value of that id
  contributed. If an item is re-indexed under the same id with different text,
  the stale tokens from the old text remain in `_index` and `_term_freq`
  (and `_doc_lengths` is overwritten to the NEW length), so a search for a
  term that only appeared in the old text still returns the item, and
  `tf`/`tfidf`/`bm25` scores are computed against a doc length that no longer
  matches the stored text. The only clean path is `remove_item` followed by
  `add_item`; there is no in-place update. This is the single most important
  hole (ticketed as ARCH-53).
