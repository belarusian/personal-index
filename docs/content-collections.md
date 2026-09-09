# content-collections — Exact Contract

Module: `personal_index/content_collections.py` (376 lines)

Content collections system for grouping saved content items into named,
public/private collections. Two public types: `Collection` (a 7-field
`@dataclass` for a single collection and its ordered item list) and
`CollectionManager` (an in-memory store keyed by collection id with a
secondary reverse index from item id to the list of collection ids that
contain it). There is no persistence and no locking; `CollectionManager` is
single-threaded and in-memory by contract (it has `serialize`/`deserialize`
helpers but no `save`/`load` and no `store_path`).

## Public API

### Collection

`@dataclass` with fields:

- `name: str`
- `collection_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])`
  — a 12-hex-char id generated at construction; there is no way to supply one.
- `description: str = ""`
- `item_ids: list[str] = field(default_factory=list)` — an **ordered** list of
  item ids; membership is order-preserving and deduplicated by the methods
  below.
- `is_public: bool = False`
- `created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())`
  — an ISO-8601 UTC timestamp string, set at construction.
- `updated_at: str | None = None` — `None` until the first mutation.

Methods:

- `add_item(self, item_id: str) -> None` — appends `item_id` to `item_ids`
  **only if it is not already present** (dedup), and refreshes
  `updated_at` to the current UTC ISO timestamp. A duplicate add is a no-op
  (no append, no `updated_at` refresh).
- `remove_item(self, item_id: str) -> None` — removes `item_id` from
  `item_ids` **only if it is present**, and refreshes `updated_at`. Removing
  an absent item is a no-op (no `updated_at` refresh).
- `contains(self, item_id: str) -> bool` — `item_id in item_ids`.
- `item_count(self) -> int` — `len(item_ids)`.
- `to_dict(self) -> dict` — returns a fresh dict with keys
  `collection_id`, `name`, `description`, `item_ids` (a **copy** of the list),
  `is_public`, `created_at`, `updated_at`.
- `from_dict(cls, data: dict) -> Collection` — classmethod. Reads
  `collection_id` (defaulting to a fresh 12-hex id when absent), `name`
  (**required** — a missing `name` raises `KeyError`), `description` (default
  `""`), `item_ids` (default `[]`), `is_public` (default `False`),
  `created_at` (defaulting to the current UTC ISO timestamp when absent; a
  `datetime` value is converted via `.isoformat()`), and `updated_at`
  (default `None`).

### CollectionManager

Plain class (not a dataclass). `__init__(self)` initializes two private
structures:

- `self._collections: dict[str, Collection]` — the primary registry, keyed by
  `collection_id`.
- `self._item_to_collections: dict[str, list[str]]` — the reverse index, keyed
  by `item_id`, value the list of `collection_id`s that contain the item.

There is no `store_path`, no `save`, no `load`, and no `clear` — the manager
is in-memory only (`serialize`/`deserialize` are the persistence boundary).

Create / read:

- `create(self, name: str, description: str = "", is_public: bool = False) -> str`
  — builds a `Collection` (fresh random id), registers it, and returns the
  `collection_id`.
- `get(self, collection_id: str) -> Collection | None` —
  `self._collections.get(collection_id)`.
- `list_all(self) -> list[Collection]` — all collections, insertion order.
- `list_public(self) -> list[Collection]` — those with `is_public` True.
- `list_private(self) -> list[Collection]` — those with `is_public` False.
- `get_items(self, collection_id: str) -> list[str]` — a **copy** of the
  collection's `item_ids`, or `[]` when the collection is absent.
- `get_collections_for_item(self, item_id: str) -> list[Collection]` — the
  `Collection` object for each id in `_item_to_collections[item_id]` that is
  **still present** in `_collections`; a dangling id is silently dropped.
  Returns `[]` for an unseen item.

Item mutation:

- `add_item(self, collection_id: str, item_id: str) -> bool` — guard path:
  returns `False` when the collection is absent (no change). On success calls
  `Collection.add_item` (dedup + `updated_at` refresh) and ensures
  `collection_id` is in `_item_to_collections[item_id]` (creating the list if
  absent, appending only if not already listed); returns `True`.
- `add_items(self, collection_id: str, item_ids: list[str]) -> None` — loops
  `add_item` over the list; returns `None` (per-item guard results are
  discarded).
- `remove_item(self, collection_id: str, item_id: str) -> bool` — guard path:
  returns `False` when the collection is absent. On success calls
  `Collection.remove_item` (a no-op when the item is absent, in which case
  `updated_at` is NOT refreshed) and cleans the reverse index: removes
  `collection_id` from `_item_to_collections[item_id]` and deletes the list
  entry entirely when it becomes empty. Returns `True` whenever the collection
  exists, **regardless of whether the item was actually present**.
- `clear_items(self, collection_id: str) -> bool` — guard path: returns `False`
  when the collection is absent. On success cleans the reverse index for every
  item in the collection (removing `collection_id` from each item's list and
  deleting the list entry when empty), clears `item_ids`, and refreshes
  `updated_at`. Returns `True` whenever the collection exists, regardless of
  whether it held any items.
- `move_item(self, item_id: str, from_collection_id: str, to_collection_id: str) -> bool`
  — returns `False` when **either** collection is absent. On success calls
  `from_c.remove_item(item_id)` then `to_c.add_item(item_id)` and reconciles
  the reverse index (removes `from_collection_id` from the item's list,
  deleting the entry when empty, then ensures `to_collection_id` is listed).
  See the contract hole below: the item does **not** need to be in the source,
  and it is removed from **only the named source**, not from every collection
  it belongs to.

Metadata mutation:

- `update_name(self, collection_id: str, new_name: str) -> bool` — sets
  `name`, refreshes `updated_at`; `False` when the collection is absent.
- `update_description(self, collection_id: str, description: str) -> bool` —
  sets `description`, refreshes `updated_at`; `False` when absent.
- `rename(self, collection_id: str, new_name: str) -> bool` — an alias for
  `update_name`.
- `toggle_public(self, collection_id: str) -> bool` — flips `is_public`,
  refreshes `updated_at`; `False` when absent.

Delete / merge:

- `delete(self, collection_id: str) -> bool` — `pop`s the collection; returns
  `False` when absent. On success cleans the reverse index for each of the
  deleted collection's items (removing `collection_id` from each item's list,
  deleting the list entry when empty) and returns `True`.
- `merge(self, target_id: str, source_id: str) -> bool` — guard path: returns
  `False` when `target_id == source_id` (a self-merge is a no-op that must not
  delete the collection or lose its items). On success (both exist and differ)
  adds every source item to the target via `target.add_item` (dedup by
  `item_id`) and ensures `target_id` is in each item's reverse-index list, then
  calls `self.delete(source_id)` (which removes `source_id` from each item's
  list). Returns `True` on success, `False` on the guard path or when either
  collection is absent. The source's `name`/`description`/`is_public`/
  `created_at` are discarded with the source; the target's metadata is
  unchanged.

Search / stats:

- `search(self, query: str) -> list[Collection]` — case-insensitive substring
  match: a collection matches when `query.lower()` is a substring of
  `name.lower()` **or** `description.lower()` (insertion order, not sorted).
- `get_recent(self, limit: int = 10) -> list[Collection]` — sorts all
  collections by `created_at` descending and returns the first `limit`;
  returns `[]` when `limit <= 0`.
- `count(self) -> int` — `len(self._collections)`.
- `get_stats(self) -> dict` — returns four keys:
  - `"total_collections"`: `len(self._collections)`.
  - `"total_items"`: the **per-collection** item count summed
    (`sum(len(c.item_ids) for c in ...)`); an item present in N collections is
    counted N times (NOT the number of distinct items).
  - `"public_collections"`: `len(self.list_public())`.
  - `"private_collections"`: `len(self.list_private())`;
    `public + private == total_collections`.
  An empty manager returns all four keys as `0`.

Persistence boundary:

- `serialize(self) -> list[dict]` — `[c.to_dict() for c in self._collections.values()]`.
- `deserialize(self, data: list[dict]) -> None` — clears **both**
  `_collections` and `_item_to_collections`, then for each dict builds a
  `Collection.from_dict`, registers it, and rebuilds the reverse index for each
  of its items. A missing `name` in any dict raises `KeyError` (from
  `from_dict`).

## Contract Holes

**Primary hole — `move_item` over-promises relocation (ARCH-43).** The name
`move_item` and its docstring ("Add the item to the destination collection and
remove it from the source collection if present") describe a relocation, but
the body performs only a **single-source remove + destination add**, and two
consequences the contract never states follow:

1. **The item does not need to be in the source.** When the item is absent
   from `from_collection_id`, `from_c.remove_item` is a no-op and the call is a
   pure **add** (a copy) into `to_collection_id` — not a move. The docstring
   states this ("the item does not need to be in the source") but the name
   still over-promises a relocation.
2. **The item is removed from only the named source, not from every collection
   it belongs to.** When the item is present in multiple collections,
   `move_item(item, C1, C2)` removes it from `C1` and adds it to `C2`, but it
   **remains in every other collection** (e.g. `C3`). So the item is not
   actually relocated out of all its collections — it ends up in `C2` *and*
   `C3`. The "move" semantic is underspecified for the multi-collection case,
   and the reverse index correctly reflects this (the item's list keeps `C3`
   and `C2`, drops `C1`), so the divergence is between the name and the body,
   not an index desync.

This is the same class of hole as the docstring over-promise defects in the
ARCH-41/42 lineage: a name/docstring that promises a stronger semantic
(relocation) than the body actually performs (single-source remove + add).

## Secondary notes (not ticketed)

- `merge`'s dedup is by `item_id` (set-union); the source's metadata is
  silently discarded with the source — documented, not a hole.
- `deserialize` on a list containing two dicts with the same `collection_id`
  overwrites the registry entry but both contribute to the reverse index; a
  malformed-input edge, not a documented contract.
