# content_annotations — Exact Contract

Module: `personal_index/content_annotations.py` (325 lines)

User notes on saved content items. Two public types: the `Annotation`
dataclass (a single note) and `AnnotationManager` (an in-memory store with
five secondary lookup indexes).

## Public API

### `AnnotationType` (str Enum)

Five members, each a `str` subclass: `NOTE = "note"`, `HIGHLIGHT =
"highlight"`, `TAG = "tag"`, `RATING = "rating"`, `FLAG = "flag"`. Because it
is a `str` Enum, `AnnotationType.NOTE == "note"` is `True` and the `.value`
attribute is the bare string.

### `Annotation` (dataclass)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| content_id | str | (required) | The saved content item this note is on |
| text | str | (required) | The note body |
| annotation_type | AnnotationType | `AnnotationType.NOTE` | One of the five enum members |
| annotation_id | str | `uuid.uuid4().hex[:12]` | 12-char hex id, generated per instance |
| author | str | `""` | Empty string means "no author" (falsy) |
| tags | list[str] | `[]` | Mutable list; shared per instance |
| position_start | int \| None | `None` | Optional char offset into the content |
| position_end | int \| None | `None` | Optional char offset into the content |
| created_at | str | `datetime.now(timezone.utc).isoformat()` | UTC ISO-8601, set at construction |
| updated_at | str \| None | `None` | Set by `update_text`/`add_tag`/`remove_tag` |

#### `update_text(self, new_text: str) -> None`

Sets `self.text = new_text` and `self.updated_at = <now UTC ISO-8601>`.
Always mutates; no guard on `new_text` (an empty string is allowed and
clears the text).

#### `add_tag(self, tag: str) -> None`

Appends `tag` to `self.tags` **only if it is not already present** (a
duplicate is a no-op). Sets `self.updated_at` on **every** call, whether or
not the tag was newly added.

#### `remove_tag(self, tag: str) -> None`

Removes the first occurrence of `tag` from `self.tags` **only if present**
(absent is a no-op). Sets `self.updated_at` on **every** call, whether or
not the tag was actually removed.

#### `to_dict(self) -> dict`

Returns a fresh dict with keys `annotation_id`, `content_id`, `text`,
`annotation_type` (the `.value` string, e.g. `"note"`), `author`, `tags`
(a **copy** — `list(self.tags)`), `position_start`, `position_end`,
`created_at`, `updated_at`.

#### `from_dict(cls, data: dict) -> Annotation` (classmethod)

- `annotation_type`: `data.get("annotation_type", "note")`; if a `str` it is
  coerced via `AnnotationType(atype)` (an unknown string **raises
  `ValueError`**); if not a `str` and not an `AnnotationType` it falls back
  to `AnnotationType.NOTE`.
- `created_at`: `data.get("created_at", <now>)`; if a `datetime` it is
  converted via `.isoformat()`.
- `content_id`: `data["content_id"]` — a **missing key raises `KeyError`**
  (the only required field; every other field has a default).
- `annotation_id`: `data.get("annotation_id", <new 12-char hex>)`.
- `text`/`author`: `data.get(..., "")`; `tags`: `data.get("tags", [])`
  (the list is **shared by reference**, not copied); `position_start`/
  `position_end`/`updated_at`: `data.get(...)` (default `None`).

### `AnnotationManager`

Holds one primary store plus five secondary indexes, all keyed by
`annotation_id`:

| Attribute | Type | Meaning |
|-----------|------|---------|
| `_annotations` | dict[str, Annotation] | The primary store (id → annotation) |
| `_by_content` | dict[str, list[str]] | content_id → [annotation_id, ...] |
| `_by_author` | dict[str, list[str]] | author → [annotation_id, ...] |
| `_by_type` | dict[str, list[str]] | annotation_type.value → [annotation_id, ...] |
| `_by_tag` | dict[str, list[str]] | tag → [annotation_id, ...] |

#### `add(self, annotation: Annotation) -> None`

Updates the primary store and all five indexes, in order:
1. `_annotations[annotation.annotation_id] = annotation` (always — a
   re-add **overwrites** the primary entry).
2. Append the id to `_by_content[annotation.content_id]` (always).
3. Append the id to `_by_author[annotation.author]` **only when
   `annotation.author` is truthy**; a falsy author leaves `_by_author`
   untouched.
4. Append the id to `_by_type[annotation.annotation_type.value]` (always).
5. Append the id to `_by_tag[tag]` for each `tag` in `annotation.tags`.

**Contract hole**: step 1 overwrites the primary store on a re-add, but
steps 2-5 **append unconditionally** — a second `add()` of the same
`annotation_id` leaves the primary store at 1 entry while each secondary
index holds 2. See Contract Holes #1.

#### `get(self, annotation_id: str) -> Annotation | None`

`self._annotations.get(annotation_id)` — `None` when absent.

#### `get_by_content_id(self, content_id: str) -> list[Annotation]`

`[self._annotations[i] for i in self._by_content.get(content_id, []) if i in
self._annotations]`. Returns `[]` for an unknown content_id. The `if i in
self._annotations` filter drops ids whose primary entry was deleted, but it
does **not** dedupe — a duplicated index entry yields the same annotation
twice (see Contract Holes #1).

#### `get_by_author(self, author: str) -> list[Annotation]`

Same shape over `_by_author`. Note: a falsy author was never indexed (see
`add`), so `get_by_author("")` is always `[]`.

#### `get_by_type(self, annotation_type: AnnotationType) -> list[Annotation]`

Same shape over `_by_type`, keyed by `annotation_type.value`.

#### `get_by_tag(self, tag: str) -> list[Annotation]`

Same shape over `_by_tag`.

#### `get_all(self) -> list[Annotation]`

`list(self._annotations.values())` — the primary store only (no index
dedup concern).

#### `get_recent(self, limit: int = 10) -> list[Annotation]`

Copies the primary store, sorts by `created_at` **descending** (newest
first), and returns `[:limit]`. **Guard**: `limit <= 0` returns `[]`
(the sort still runs, but the slice is empty).

#### `update_text(self, annotation_id: str, new_text: str) -> bool`

`True` and mutates when the id is present; `False` (no mutation) when absent.

#### `add_tag(self, annotation_id: str, tag: str) -> None`

No-op when the id is absent. When present: calls `annotation.add_tag(tag)`
and appends the id to `_by_tag[tag]` **only if the tag was newly added** to
the annotation (a duplicate tag on the annotation does not re-append to the
index).

#### `remove_tag(self, annotation_id: str, tag: str) -> None`

No-op when the id is absent. When present: calls `annotation.remove_tag(tag)`
and, if `tag` is a key in `_by_tag`, filters the id out of `_by_tag[tag]`
(the key is **not** deleted even when the list becomes empty).

#### `delete(self, annotation_id: str) -> bool`

`self._annotations.pop(annotation_id, None)`; `False` (no mutation) when
absent. When present, removes the id from all five indexes:
- `_by_content[cid]`: filtered; the key is **deleted** when the list becomes
  empty.
- `_by_author[author]`: filtered; the key is **not** deleted when empty.
- `_by_type[type_key]`: filtered; the key is **not** deleted when empty.
- `_by_tag[tag]` for each tag: filtered; the key is **not** deleted when
  empty.

Returns `True`.

#### `delete_by_content_id(self, content_id: str) -> int`

`ids = self._by_content.pop(content_id, [])`; calls `self.delete(aid)` for
each and returns the count of successful deletes. Returns `0` for an unknown
content_id.

#### `search(self, query: str) -> list[Annotation]`

Case-insensitive substring match: `query.lower() in ann.text.lower()` over
the primary store, in insertion order. Returns `[]` when nothing matches.
An empty `query` matches **every** annotation (empty string is a substring
of all).

#### `count(self) -> int`

`len(self._annotations)` — the primary store size (never the index sizes).

#### `get_stats(self) -> dict`

Returns a dict with exactly three keys:
1. `"total"`: `len(self._annotations)`.
2. `"by_content"`: `len(self._by_content)` — the number of **distinct**
   content ids with at least one annotation (NOT the total annotation count).
3. `"by_type"`: a `dict[str, int]` mapping each `AnnotationType.value`
   present to its annotation count; absent types are omitted.

No mutation.

#### `clear(self) -> None`

Clears the primary store and all five indexes.

#### `serialize(self) -> list[dict]`

`[ann.to_dict() for ann in self._annotations.values()]` — insertion order.

#### `deserialize(self, data: list[dict]) -> None`

`self.clear()`, then `Annotation.from_dict(item)` + `self.add(ann)` for each
item. A missing `content_id` in any item raises `KeyError` (from
`from_dict`); an unknown `annotation_type` string raises `ValueError`.

## Contract Holes

### 1. `add()` is not idempotent — re-adding an `annotation_id` diverges the secondary indexes from the primary store

`add()` sets `_annotations[annotation.annotation_id] = annotation`
(line 136), which **overwrites** the primary entry on a re-add. But the
secondary-index appends (lines 141, 147, 152, 157) are **unconditional** —
they do not check whether the id is already present. So a second `add()` of
the same `annotation_id` leaves:

- `_annotations` at **1** entry (dict overwrite), so `count()` / `get_all()`
  / `get_stats()["total"]` all report 1.
- `_by_content[cid]`, `_by_type[type]`, and (when author/tags are present)
  `_by_author[author]` / `_by_tag[tag]` each at **2** entries.

Consequences (verified):
- `get_by_content_id(cid)` returns the **same annotation twice** (the `if i
  in self._annotations` filter in `get_by_content_id` does not dedupe).
- `get_by_author` / `get_by_type` / `get_by_tag` likewise return duplicates.
- `get_stats()["by_content"]` (a `len` of the index) can disagree with
  `get_stats()["total"]` after a re-add.

The primary store and the secondary indexes are the two sources of truth for
the same set of annotations, and `add()` is the only method that can make
them disagree. `delete()` is symmetric in the opposite direction (it filters
every index), so the divergence is introduced only by a duplicate `add()`.

### 2. `from_dict` raises `KeyError` on a missing `content_id` (no guard)

`from_dict` reads `content_id=data["content_id"]` (line 95) with a raw
subscript — the only field without a `.get` default. A dict missing
`content_id` raises `KeyError` rather than falling back to a default or
raising a typed error. This propagates through `AnnotationManager.deserialize`
(a single malformed item aborts the whole batch after `clear()` has already
emptied the store, so a partial deserialize leaves the manager empty).

## Secondary notes

- `get_stats()["by_content"]` counts **distinct content ids**, not
  annotations — two annotations on one content id count once.
- `delete()` deletes the `_by_content[cid]` key when its list empties, but
  leaves empty `_by_author` / `_by_type` / `_by_tag` keys in place (asymmetric
  cleanup; harmless for lookups, but the index dicts can accumulate empty
  lists).
- `search("")` matches every annotation (empty substring).
- `get_recent` sorts by the `created_at` **string**; ISO-8601 UTC strings
  sort chronologically, so this is correct for the default factory, but a
  manually-set non-ISO `created_at` would sort lexicographically.
- `Annotation.tags` is a mutable list shared by reference between the
  annotation and (after `from_dict`) the deserialized dict's list — mutating
  one is visible through the other.
