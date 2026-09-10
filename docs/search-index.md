# Search Index (`personal_index.index`)

Status: **spec** — audited against current code (cycle 169).

`SearchIndex` is a `@dataclass` with `db_path: str | None`, an in-memory
`_pages: dict[str, IndexedPage]` and a `_word_index: dict[str, list[str]]`.
On construction, if `db_path` exists it is loaded via `_load()` (corrupt /
non-dict JSON resets both to empty).

## Methods
- `add_page(page: IndexedPage | CrawledPage) -> int` — accepts either model;
  a `CrawledPage` is converted to an `IndexedPage` (domain via
  `url_utils.extract_domain`, `content_length=len(content)`, etc.). Adds to
  `_pages`, updates `_word_index` (tokenized title+content, stop words and
  single-char tokens filtered), persists via `_save()`. **Returns the new page
  count** (`len(self._pages)`), not a page id.
- `remove_page(url) -> bool` — False if url absent; else pops the page,
  prunes its urls from every `_word_index` token (deleting empty tokens),
  persists, returns True.
- `get_page(url) -> IndexedPage | None`.
- `get_page_count() -> int`.
- `list_pages() -> list[IndexedPage]` — sorted by `score` descending.
- `clear()` — empties both structures, persists.
- `search(query, limit=10) -> list[SearchResult]` — guard: empty query, no
  tokens, or `limit <= 0` -> `[]`. Scores each candidate url as
  `title_count*3.0 + content_count*1.0 + page.score*0.5` summed over query
  tokens; returns the top `limit` as `SearchResult` (snippet via
  `_create_snippet`, `matched_terms` left empty).
- `close()` — persists. Context-manager supported.

## Contract holes
- **`add_page` docstring drift (-> ARCH-4) — RESOLVED.** The docstring
  previously read "Returns page id." but the body returns `len(self._pages)` —
  the new page **count**, not an id. The docstring has since been reworded to
  "Returns the new page count, len(self._pages) (an int). NOT a page id." to
  match the code. ARCH-4 is resolved.
- **`search` docstring drift — RESOLVED.** The docstring was a single blanket
  line ("Search the index.") that did not enumerate the guard path or the
  scoring formula. It has since been reworded to enumerate all guard paths
  (empty query / no tokens / `limit <= 0` -> `[]`) and the exact scoring
  formula. The doc now matches the code.
