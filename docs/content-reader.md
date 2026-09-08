# Content Reader (spec)

`personal_index.content_reader` — an in-memory reader for browsing content
items that were added by the caller via `add` / `add_many`. It provides
pagination, tag/score filtering, title/content substring search, and
display formatting. It is a pure in-memory module: **no network I/O, no file
I/O, no persistence** — the reader holds no state beyond what the caller
adds, and it is not wired to any store or pipeline (nothing in
`personal_index/` imports it).

The module exports three names: `ReadResult` (a `@dataclass`), `PageView`
(a `@dataclass`), and `ContentReader`.

## Public API

### `ReadResult`
A `@dataclass` describing one content item.

Fields (the first three are required; the last three have defaults):
- `url: str` — the item's URL (the lookup key for `get`).
- `title: str` — the item's title.
- `content: str` — the item's body text.
- `tags: list[str] = field(default_factory=list)` — item tags.
- `score: float = 0.0` — item score.
- `metadata: dict[str, Any] = field(default_factory=dict)` — free-form
  metadata.

#### `to_dict(self) -> dict[str, Any]`
Returns a plain dict with exactly the six fields above, in the order
`url`, `title`, `content`, `tags`, `score`, `metadata`. The `tags` and
`metadata` values are the **same list/dict objects** held by the dataclass
(not copies), so mutating the returned dict's `tags`/`metadata` mutates the
item.

### `PageView`
A `@dataclass` describing one page of a paginated result.

Fields (all required):
- `items: list[ReadResult]` — the items on this page.
- `page: int` — the 1-based page number (already clamped by `paginate`).
- `page_size: int` — the requested page size.
- `total_items: int` — the total number of items across all pages.
- `total_pages: int` — the total number of pages (at least 1).
- `has_next: bool` — whether a later page exists.
- `has_prev: bool` — whether an earlier page exists.

Properties:
- `start_index -> int` — `(page - 1) * page_size` (0-based index of the
  first item on this page).
- `end_index -> int` — `min(start_index + page_size, total_items)` (0-based
  index one past the last item on this page).

### `ContentReader`
Holds two private structures: `_items: list[ReadResult]` (insertion order)
and `_url_index: dict[str, ReadResult]` (URL → item, last-write-wins).

#### `__init__(self) -> None`
Initializes an empty reader (`count == 0`).

#### `add(self, item: ReadResult) -> None`
Appends `item` to `_items` **and** sets `_url_index[item.url] = item`.
There is **no dedup and no error** on a repeated URL — see contract hole 1.

#### `add_many(self, items: list[ReadResult]) -> None`
Calls `add` for each item in `items` (in order).

#### `get(self, url: str) -> ReadResult | None`
Returns `_url_index.get(url)` — the **last** item added for `url`, or `None`
if no item has that URL.

#### `list_all(self) -> list[ReadResult]`
Returns a shallow copy of `_items` in insertion order (a new list; the
`ReadResult` objects are shared).

#### `paginate(self, page: int = 1, page_size: int = 10, sort_by: str = "score", reverse: bool = True) -> PageView`
- **Guard path (`page_size < 1`):** raises `ValueError("Page size must be >= 1")`.
- **Normal path:** sorts a copy of `_items` by `sort_by` (see `_sort_items`
  below) with `reverse` (default `True` = descending), then:
  - `total_items = len(items)`; `total_pages = max(1, ceil(total_items / page_size))`.
  - `page` is **clamped** to `[1, total_pages]` (an out-of-range `page`
    silently becomes the last valid page, not an error).
  - Returns a `PageView` with `has_next = page < total_pages` and
    `has_prev = page > 1`.
- **Empty reader:** returns a 1-page view with 0 items
  (`total_items=0`, `total_pages=1`, `has_next=False`, `has_prev=False`).

#### `_sort_items(items, sort_by, reverse) -> list[ReadResult]` (staticmethod, private)
Sorts `items` in place by:
- `"score"` → `item.score`
- `"title"` → `item.title.lower()` (case-insensitive)
- `"url"` → `item.url.lower()` (case-insensitive)
- **any other value → no sort** (insertion order is preserved; a typo in
  `sort_by` is a silent no-op, not an error).

#### `filter_by_tags(self, tags: list[str], match_all: bool = False) -> list[ReadResult]`
- **Guard path (empty `tags`):** returns `list(self._items)` — the **full**
  list, not an empty result (see contract hole 3).
- **Normal path:** compares lower-cased tag sets. `match_all=True` keeps an
  item only if `tags ⊆ item.tags`; `match_all=False` keeps an item if the
  two sets intersect (any match). Matching is case-insensitive on both sides.

#### `filter_by_score(self, min_score: float = 0.0, max_score: float | None = None) -> list[ReadResult]`
Keeps items where `item.score >= min_score` **and** (`max_score is None` or
`item.score <= max_score`). Both bounds are inclusive.

#### `search_titles(self, query: str) -> list[ReadResult]`
Case-insensitive substring match of `query` against `item.title`.

#### `search_content(self, query: str) -> list[ReadResult]`
Case-insensitive substring match of `query` against `item.content`.

#### `format_item(self, item: ReadResult, show_content: bool = True) -> str`
Builds a display string:
- Always: `## {title}`, `URL: {url}`, `Score: {score:.2f}` (score to 2
  decimals).
- If `item.tags` is non-empty: `Tags: {', '.join(item.tags)}`.
- If `show_content` **and** `item.content` is non-empty: a blank line, then
  `item.content[:500]`, and — only if `len(item.content) > 500` — a trailing
  `...` line. (Exactly 500 chars → no ellipsis; 501+ → 500 chars + `...`.)
- Joins with `"\n"`.

#### `format_page(self, page_view: PageView, show_content: bool = True) -> str`
Builds a display string:
- Header: `Page {page} of {total_pages}`, then
  `Showing {start_index + 1}-{end_index} of {total_items} items`, then a
  blank line.
- For each item: `format_item(item, show_content)`, then `---`, then a blank
  line.
- If `has_prev` or `has_next`: a final line joining `[Prev Page {page-1}]`
  and/or `[Next Page {page+1}]` with ` | `.
- Joins with `"\n"`. Note: for an empty reader's page view this renders
  `Showing 1-0 of 0 items` (an inverted range, since `start_index + 1 = 1`
  but `end_index = 0`).

#### `clear(self) -> None`
Empties both `_items` and `_url_index` (`count` becomes 0).

#### `count -> int` (property)
`len(self._items)` — the number of items in insertion order.

## Contract holes
1. **Duplicate URLs make `get` and the collection views disagree.** `add`
   appends to `_items` but overwrites `_url_index[item.url]`. After adding
   two items with the same URL, `count` / `list_all` / `paginate` /
   `filter_by_*` / `search_*` all see **both** items (they iterate
   `_items`), but `get(url)` returns only the **last** one added (dict
   overwrite). The URL is documented as the lookup key ("Get a content item
   by URL"), yet the reader is not a set keyed by URL: there is no dedup, no
   error, and no documented last-write-wins policy, so `get(url)` and
   `list_all()` are internally inconsistent for repeated URLs. (Most
   important hole — ticketed as **ARCH-27**.)
2. **`format_page` renders an inverted range for an empty reader.** For an
   empty reader, `paginate()` returns `start_index=0`, `end_index=0`,
   `total_items=0`, so `format_page` emits `Showing 1-0 of 0 items`
   (`start_index + 1 = 1` exceeds `end_index = 0`). The header is not
   guarded for the zero-item case.
3. **`filter_by_tags([])` returns the full list, not an empty result.** The
   empty-`tags` guard returns `list(self._items)` (a no-op "no filter"),
   which is the opposite of what "filter by these tags" would suggest for an
   empty tag set. It is a documented-in-code guard but a surprising contract:
   an empty filter matches everything rather than nothing.

## Tests
`tests/test_content_reader.py` pins `to_dict`, the `PageView` index
properties, `add`/`get` (hit + miss), `list_all`, `paginate` (default
score-descending sort, second page, title sort, out-of-range clamp, and the
`page_size < 1` `ValueError`), `filter_by_tags` (any / all / empty),
`filter_by_score` (min / range), `search_titles` (case-insensitive),
`search_content`, `format_item` (with / without content, 500-char
truncation + ellipsis, `show_content=False`), `format_page`, `clear`,
`count`, and a fresh-reader-is-empty guard. The duplicate-URL divergence
(contract hole 1) is **not** currently pinned — see ARCH-27.
