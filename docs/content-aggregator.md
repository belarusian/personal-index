# content_aggregator — Exact Contract

Module: `personal_index/content_aggregator.py` (72 lines)

Aggregates content from multiple named sources into a single list, with
optional deduplication. One public type: `ContentAggregator` (a plain class,
no dataclasses). Sources are stored as `dict[str, list[dict[str, Any]]]`
insertion-ordered; every item is a plain dict keyed on string fields.

## Public API

### ContentAggregator

State: `_sources: dict[str, list[dict[str, Any]]]` (insertion-ordered) and
`_merged: list[dict[str, Any]]` (initialized to `[]` but **never read or
written** — see contract holes).

#### Methods

- `__init__(self) -> None`
  Initializes `_sources = {}` and `_merged = []`. No arguments.

- `add_source(self, name: str, items: list[dict[str, Any]]) -> None`
  Stores a **shallow copy** of `items` (`list(items)`) under `name`.
  **Overwrites** any existing source with the same `name` (no merge, no
  error). The outer list is copied but the inner dicts are shared by
  reference with the caller.

- `get_source(self, name: str) -> list[dict[str, Any]]`
  Returns the stored list for `name`, or `[]` if `name` is unknown.
  Returns the **stored list by reference** (mutating the result mutates the
  aggregator's state).

- `merge_all(self, deduplicate: bool = True) -> list[dict[str, Any]]`
  Concatenates all sources in **source insertion order** (the order
  `add_source` was first called for each name). When `deduplicate` is `True`
  (the default), removes duplicate items keyed on
  `str(item.get("id") or item.get("title"))`, keeping the **first**
  occurrence. When `deduplicate` is `False`, returns every item with no
  dedup. The returned list contains **references to the stored item dicts**
  (aliasing — see contract holes).

- `filter_by_source(self, source_name: str) -> list[dict[str, Any]]`
  **Byte-identical to `get_source`** (same body, same `[]` fallback). A dead
  alias — see contract holes.

- `get_source_names(self) -> list[str]`
  Returns `list(self._sources.keys())` — all source names in insertion order.

- `clear_source(self, name: str) -> bool`
  Deletes `name` from `_sources`; returns `True` if it existed, `False`
  otherwise.

- `clear_all(self) -> None`
  Empties `_sources`. Does **not** touch `_merged`.

#### Properties

- `total_items(self) -> int`
  `sum(len(items) for items in self._sources.values())` — total items across
  all sources, **before** any merge/dedup.

- `source_count(self) -> int`
  `len(self._sources)` — number of distinct source names.

## Contract Holes

### (ARCH-35) `merge_all` dedup key collapses items with both `id` and `title` falsy — silent data loss on the default path

The dedup key is `str(item.get("id") or item.get("title"))`. The `or` chain
falls through to the next operand whenever `id` is **falsy** (absent, `None`,
`""`, `0`, `False`), and `str()` is applied to the result. Two distinct
failure modes follow:

- **Both `id` and `title` absent/falsy → one shared key.** An item with no
  `id` and no `title` yields `str(None or None)` = `"None"`; an item with
  `id=""` and `title=""` yields `str("" or "")` = `""`. Every such item in
  the merged stream maps to the *same* key, so with the **default**
  `deduplicate=True` only the **first** of them survives and the rest are
  silently dropped. This is data loss on the default code path with no
  warning, no error, and no way for the caller to detect it from the returned
  list.
- **`str()` collapses distinct id types.** `id=1` (int) and `id="1"` (str)
  both key to `"1"` and are treated as duplicates; likewise a falsy `id=0`
  falls back to `title` even though `0` is a legitimate id.

The docstring says "keyed on the item's `id` (falling back to `title`)" but
never states that items lacking both are collapsed, so the over-promise is
hidden. This is the single most important hole in the module: it is the only
behavior that silently **loses data** on the default call.

### Secondary holes (documented, not separately ticketed)

- **`filter_by_source` is a dead alias of `get_source`.** Identical body and
  `[]` fallback; one of the two should be removed or one should delegate to
  the other.
- **`self._merged` is dead state.** Initialized to `[]` in `__init__` but
  never read or written anywhere; `merge_all` returns a fresh list each call
  and never populates it.
- **Aliasing.** `merge_all` and `get_source` return references to the stored
  item dicts (and `add_source` shares the inner dicts with the caller), so
  mutating a returned item mutates the aggregator's state.
