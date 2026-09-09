# bookmarks — Exact Contract

Module: `personal_index/bookmarks.py` (175 lines)

In-memory bookmark store with optional JSON persistence. Two public types:
`Bookmark` (a `@dataclass`) and `BookmarkManager` (a plain class holding a
`dict[str, Bookmark]` keyed by URL). There is no locking; the manager is
single-threaded by contract.

## Public API

### Bookmark

A `@dataclass` with eight fields (order matters for positional construction):

- `url: str` — required, the store key.
- `title: str = ""`
- `description: str = ""`
- `category: str = "uncategorized"`
- `tags: list[str] = field(default_factory=list)`
- `created_at: str = ""` — ISO-8601 UTC string.
- `updated_at: str = ""` — ISO-8601 UTC string.
- `is_favorite: bool = False`

Behavior:

- `__post_init__`: if `created_at` is empty it is set to
  `datetime.now(timezone.utc).isoformat()`; if `updated_at` is empty it is set
  to the (possibly just-filled) `created_at`. Explicit timestamps are kept as
  given — no parsing, no validation.
- `to_dict() -> dict`: returns all eight fields under their exact names.
- `from_dict(cls, data: dict) -> Bookmark`: classmethod. `url` is read with
  `data["url"]` (a missing key raises `KeyError`); every other field uses
  `data.get(...)` with the dataclass default (`category` defaults to
  `"uncategorized"`, `tags` to `[]`, `is_favorite` to `False`).

### BookmarkManager

`__init__(self, storage_path: str | None = None)` — empty
`_bookmarks: dict[str, Bookmark]`; `storage_path` is the default for
`save`/`load`.

- `add(bookmark: Bookmark) -> Bookmark` — upsert keyed by `bookmark.url`. On
  collision the existing `created_at` is copied onto the incoming bookmark;
  every other field (title, description, category, tags, is_favorite) is
  overwritten by the incoming object. `updated_at` is always set to now.
  Returns the stored (mutated) bookmark.
- `get(url: str) -> Bookmark | None` — exact-URL lookup.
- `remove(url: str) -> bool` — deletes and returns `True` if present,
  `False` otherwise.
- `list_all() -> list[Bookmark]` — all values in insertion order.
- `list_by_category(category: str) -> list[Bookmark]` — exact category match.
- `list_by_tag(tag: str) -> list[Bookmark]` — `tag in b.tags` membership.
- `list_favorites() -> list[Bookmark]` — `is_favorite` is `True`.
- `toggle_favorite(url: str) -> Bookmark | None` — flips `is_favorite`,
  refreshes `updated_at`; returns `None` for an unknown URL (no error).
- `search(query: str) -> list[Bookmark]` — case-insensitive substring match
  against title OR description OR url.
- `get_categories() -> list[str]` — sorted unique categories.
- `get_all_tags() -> list[str]` — sorted unique tags across all bookmarks.
- `count() -> int` — number of stored bookmarks.
- `save(path: str | None = None) -> str` — writes the list of `to_dict()`
  payloads as indented JSON to `path or storage_path`; raises `ValueError`
  when neither is set. Does NOT create parent directories (a missing parent
  raises `FileNotFoundError`). Returns the path written.
- `load(path: str | None = None) -> int` — reads JSON from
  `path or storage_path`; raises `ValueError` when neither is set. Returns
  `0` without touching the current set when the file is missing, the JSON is
  malformed (`JSONDecodeError`), or the top-level value is not a list.
  Otherwise **clears the current set** and replaces it with the loaded
  bookmarks (deduped by URL, last occurrence wins), returning the count
  loaded.

## Contract Holes

Primary hole (ARCH-39): `load` is a silent full replacement. Any in-memory
bookmarks that were never `save`d are discarded with no warning, no return
value distinguishing "replaced N" from "lost M unsaved", and no merge/append
mode. The only persistence round-trip is save-then-load, so the hole bites
exactly when a caller mutates the store, calls `load` (e.g. to pick up
another process's file), and loses the unsaved mutations. The fix must make
the merge/replace semantic explicit (e.g. a `merge: bool = False` parameter
that upserts loaded bookmarks over the current set, preserving existing
`created_at` on URL collision, mirroring `add`), keep the default as
replace for backward compatibility, and report the outcome unambiguously.

Secondary holes (documented, not ticketed):

- `add` collision semantics are asymmetric: `created_at` is preserved but
  `is_favorite`/`tags`/`category` are clobbered by the incoming object — an
  `add` of a bare `Bookmark(url=...)` silently strips the existing
  bookmark's tags and favorite flag.
- `from_dict` raises `KeyError` on a missing `url` while every other field
  has a default, so one malformed entry in a saved file aborts the whole
  `load` mid-loop after `_bookmarks.clear()` has already run — a partially
  loaded, corrupted store.
- `save` does not create parent directories.
