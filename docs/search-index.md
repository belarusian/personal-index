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
- `search(query, limit=10) -> list[SearchResult]` — guard: empty query or no
  tokens -> `[]`. Scores each candidate url as
  `title_count*3.0 + content_count*1.0 + page.score*0.5` summed over query
  tokens; returns the top `limit` as `SearchResult` (snippet via
  `_create_snippet`, `matched_terms` left empty).
- `close()` — persists. Context-manager supported.

## Contract holes
- **`add_page` docstring drift (-> ARCH-4).** The docstring reads "Returns page
  id." but the body returns `len(self._pages)` — the new page **count**, not an
  id. The docstring over-promises a "page id" that does not exist.
- **`search` docstring drift.** The docstring is a single blanket line ("Search
  the index.") that does not enumerate the guard path (empty query -> `[]`) or
  the scoring formula.
