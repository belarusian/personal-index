# Search Index (`personal_index.search_index`)

Status: **spec** — audited against current code (cycle 239).

`SearchIndex` is a `@dataclass` with `index_path: str`, an in-memory
`_pages: dict[str, CrawledPage]` and a `_word_index: dict[str, list[str]]`.
On construction, `__post_init__` calls `_load()`. This is a **distinct module
from `personal_index.index`** (covered by `search-index.md`): the class here
is keyed on `index_path` (not `db_path`), stores `CrawledPage` objects (not
`IndexedPage`), exposes `add`/`remove`/`get`/`count`/`urls` (not
`add_page`/`remove_page`/`get_page`/`list_pages`), returns raw `(url, float)`
tuples from `search` (not `SearchResult`), and has no `close()` /
context-manager. It is a live production module — imported by
`personal_index/stats.py`, `personal_index/scheduler.py`, and
`personal_index/results.py` (see Secondary notes).

## Public API

### `SearchIndex`

    @dataclass
    class SearchIndex:
        index_path: str
        _pages: dict[str, CrawledPage] = field(default_factory=dict, repr=False)
        _word_index: dict[str, list[str]] = field(default_factory=dict, repr=False)
        def __post_init__(self) -> None
        @staticmethod
        def _tokenize(text: str) -> list[str]
        def _load(self) -> None
        def _save(self) -> None
        def add(self, page: CrawledPage) -> None
        def remove(self, url: str) -> bool
        def get(self, url: str) -> CrawledPage | None
        def count(self) -> int
        def clear(self) -> None
        def urls(self) -> list[str]
        def search(self, query: str, limit: int = 10) -> list[tuple[str, float]]

- `__post_init__()`: calls `self._load()`. No other initialization.
- `_tokenize(text)` (staticmethod): `re.findall(r"[a-z0-9]+", text.lower())` —
  lowercase alphanumeric runs, punctuation/whitespace dropped. **Guard path:**
  `if not text: return []` — an empty string, `None`, or any falsy input
  yields `[]`. A string with no `[a-z0-9]` characters (e.g. `"---"`) also
  yields `[]`.
- `_load()`: **missing file** → both structures set to `{}` and return.
  **Valid dict** → rebuilds `_pages` by calling `CrawledPage.from_dict` on each
  entry of `data["pages"]` and sets `_word_index = data.get("word_index", {})`.
  **Non-dict top-level** (e.g. a JSON list or scalar) → `return` with both
  structures left at their dataclass defaults (`{}`). **Corrupt / partial
  JSON** (a `json.JSONDecodeError`, or a `KeyError`/`AttributeError` raised
  while rebuilding) → both structures reset to `{}`. The degrade-to-empty
  behavior on corrupt input is pinned by
  `tests/deep/test_defensive_load_sweep_adversarial.py` (Site 2) and must not
  change.
- `_save()`: `Path(index_path).parent.mkdir(parents=True, exist_ok=True)`,
  serializes every page to an 11-key dict (`url`, `title`, `content`,
  `meta_description`, `status_code`, `depth`, `parent_url`, `headers`,
  `matched_interests`, `relevance_score`, `crawled_at` as
  `page.crawled_at.isoformat()`), then
  `with open(self.index_path, "w") as f: json.dump(data, f, indent=2)`.
  **The write is non-atomic and is neither flushed nor fsynced** — see
  Contract Hole 1.
- `add(page)`: `self._pages[page.url] = page` (a re-add of the same url
  **overwrites** the stored page). Tokenizes `f"{page.title} {page.content}".lower()`
  and, for each **unique** token, appends `page.url` to `_word_index[token]`
  if not already present (so a url appears at most once per token). Persists
  via `_save()`. Returns `None`.
- `remove(url)`: **False** if `url not in self._pages`. Otherwise pops the
  page, then iterates a **copy** of the `_word_index` keys and removes `url`
  from each token's posting list, deleting the token entirely when its list
  becomes empty; persists via `_save()`; returns **True**. The word index is
  fully pruned (no stale postings leak).
- `get(url)`: `self._pages.get(url)` — the stored `CrawledPage` **by
  reference**, or `None`.
- `count()`: `len(self._pages)`.
- `clear()`: sets both structures to `{}` and persists via `_save()`.
  Idempotent.
- `urls()`: `list(self._pages.keys())` — insertion order, a fresh list.
- `search(query, limit=10)`: **Guard paths** (each returns `[]`):
  `limit <= 0`; empty/`None` query; or a query that tokenizes to no tokens.
  Otherwise, for each query token present in `_word_index`, each candidate url
  is scored as `title_count * 3.0 + content_count * 1.0 +
  page.relevance_score * 0.5`, where `title_count = page.title.lower().count(token)`
  and `content_count = page.content.lower().count(token)` (substring counts,
  summed over all query tokens). Results are sorted by score descending and the
  top `limit` are returned as `(url, float)` tuples. A candidate url whose
  page is missing from `_pages` is skipped (no score).

## Contract Holes

### Hole 1 — `_save` is non-atomic and unflushed, so a crash mid-write truncates the index and the next `_load` silently loses all data (ARCH-71)

`_save` opens the target file with mode `"w"`, which **truncates the existing
file to zero bytes before any byte is written**, then calls `json.dump` with
**no `f.flush()` and no `os.fsync(f.fileno())`**. Two consequences:

1. **Truncation on crash.** If the process is killed (or the disk fills)
   between the `open(..., "w")` truncation and the completion of `json.dump`,
   the file on disk is left **empty or partial** — a truncated JSON document.
   Because `add`/`remove`/`clear` all call `_save` on every mutation, a single
   interrupted write destroys the entire persisted index.
2. **Silent total data loss on reload.** The next `SearchIndex(index_path)`
   construction runs `_load`, which hits `json.JSONDecodeError` on the
   truncated file and **resets both `_pages` and `_word_index` to `{}`** (the
   defensive degrade pinned by the deep test). The caller sees an empty index
   with no error, no log, and no signal that data was lost.

The covered sibling module `personal_index.index.SearchIndex._save`
(`search-index.md`) does the opposite: it calls `f.flush()` and
`os.fsync(f.fileno())` after `json.dump`, and (with the ARCH-71 fix below)
should write atomically. The two `SearchIndex` classes in this package
therefore have **divergent durability guarantees** for the same
"persist the index" operation. This is the same "advertised safety not
actually provided" class as the ARCH-66/67/68/69/70 holes: the docstring
"Save index to file." implies a durable save, but the body provides neither
durability (flush/fsync) nor atomicity (temp-file + rename).

**Fix direction (implementer):** make `_save` atomic and durable — serialize
to a temp file in the same directory, `f.flush()` + `os.fsync(f.fileno())`,
then `os.replace(tmp, self.index_path)` (atomic on POSIX). The `_load`
degrade-to-empty behavior on genuinely corrupt input must remain unchanged
(it is pinned). See `tickets/ARCH-71.md`.

## Secondary notes

- **Live production module.** `grep -rn "from personal_index.search_index"`
  shows it imported by `personal_index/stats.py`, `personal_index/scheduler.py`,
  and `personal_index/results.py` — it is wired into the pipeline, not
  orphaned. (The `cli_verify.py` `SearchIndex(db_path=...)` references are the
  **other** `SearchIndex` from `personal_index.index`, not this one.)
- **`_load` silent degrade is pinned, not a defect.** The reset-to-`{}` on
  corrupt/non-dict JSON is intentional defensive behavior pinned by
  `tests/deep/test_defensive_load_sweep_adversarial.py` (Site 2). It is the
  *consequence* half of Hole 1; the *cause* half (the non-atomic `_save`) is
  what ARCH-71 targets.
- **Scoring uses substring counts, not token counts.** `search` scores with
  `page.title.lower().count(token)` / `page.content.lower().count(token)`,
  which count substring occurrences (e.g. `"cat"` inside `"category"`).
  Candidate selection, however, is exact-token (via `_word_index`), so a query
  token only matches urls that contain that exact token at add time. This is a
  scoring nuance, not a cross-method divergence; documented for completeness.
