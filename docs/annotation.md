# annotation — Exact Contract

Module: `personal_index/annotation.py` (205 lines)

Content annotation system for marking and categorizing indexed content. Three
public types: `AnnotationType` (a `str` `Enum` of the seven annotation kinds),
`Annotation` (an 8-field `@dataclass` for a single annotation), and
`AnnotationStore` (an in-memory store keyed by annotation id with a secondary
index by URL). There is no persistence and no locking; `AnnotationStore` is
single-threaded and in-memory by contract (unlike `TagStore`/`Storage`, it has
no `save`/`load` and no `store_path`).

## Public API

### AnnotationType

`class AnnotationType(str, Enum)` with seven members, each value the lowercase
name:

- `HIGHLIGHT = "highlight"`
- `NOTE = "note"`
- `TAG = "tag"`
- `RATING = "rating"`
- `CATEGORY = "category"`
- `BOOKMARK = "bookmark"`
- `FLAG = "flag"`

Because it is a `str` `Enum`, each member compares equal to its string value
(`AnnotationType.NOTE == "note"` is `True`), so a raw `"note"` string is
accepted anywhere an `AnnotationType` is expected.

### Annotation

`@dataclass` with fields:

- `annotation_id: str`
- `url: str`
- `annotation_type: AnnotationType`
- `value: Any = None`
- `metadata: dict = field(default_factory=dict)`
- `created_at: float = field(default_factory=time.time)` — set to the current
  epoch time at construction.
- `updated_at: float | None = None`
- `author: str = ""`

Methods:

- `update(self, value: Any = None, metadata: dict | None = None) -> None`
  — if `value is not None` it replaces `self.value`; if `metadata is not None`
  it **merges** into `self.metadata` via `dict.update` (existing keys are
  overwritten, new keys added, keys absent from the argument are kept); then
  sets `self.updated_at = time.time()`. Passing both `None` still bumps
  `updated_at` (a no-op update is still an update).
- `to_dict(self) -> dict` — returns a fresh dict with keys
  `annotation_id`, `url`, `type` (the **string value** of `annotation_type`,
  not the enum member and not the field name `annotation_type`), `value`,
  `metadata`, `created_at`, `updated_at`, `author`. There is no `from_dict`
  counterpart.

### AnnotationStore

Plain class (not a dataclass). `__init__(self)` initializes two private
structures:

- `self._annotations: dict[str, Annotation]` — the primary registry, keyed by
  `annotation_id`.
- `self._by_url: dict[str, list[str]]` — the secondary index, keyed by `url`,
  value the list of `annotation_id`s recorded for that URL.

There is no `store_path`, no `save`, no `load`, and no `clear` — the store is
in-memory only.

Registry:

- `add(self, annotation: Annotation) -> None` — assigns
  `self._annotations[annotation.annotation_id] = annotation` (a dict
  assignment, so an existing id is **overwritten in place**); then, if the
  annotation's `url` is not yet a key in `_by_url`, creates its list, and if
  the `annotation_id` is not already in that URL's list, appends it. See the
  contract hole below for the id-collision behavior.
- `get(self, annotation_id: str) -> Annotation | None` —
  `self._annotations.get(annotation_id)`.
- `update(self, annotation_id: str, value: Any = None, metadata: dict | None = None) -> bool`
  — returns `False` when the id is not present (a no-op). Otherwise calls
  `annotation.update(value, metadata)` on the stored object and returns
  `True`.
- `remove(self, annotation_id: str) -> bool` — `pop`s the id from
  `_annotations`; returns `False` when absent. Otherwise, if the annotation's
  `url` is a key in `_by_url`, rebuilds that URL's list excluding the removed
  id, and returns `True`.

URL index:

- `get_by_url(self, url: str) -> list[Annotation]` — returns the `Annotation`
  object for each id in `_by_url[url]` that is **still present** in
  `_annotations`; a dangling id (recorded in the index but no longer in the
  registry) is silently dropped, so the result may be shorter than the
  recorded id list. Returns `[]` for an unseen URL.
- `remove_by_url(self, url: str) -> int` — `pop`s the URL's id list from
  `_by_url` (empty list when unseen), deletes each still-present id from
  `_annotations`, and returns the number actually deleted.

Type filter:

- `get_by_type(self, annotation_type: AnnotationType) -> list[Annotation]` —
  returns every annotation whose `annotation_type == annotation_type`
  (insertion order, not sorted).

Search:

- `search(self, query: str) -> list[Annotation]` — case-insensitive substring
  match: an annotation matches when `query.lower()` is a substring of
  `annotation.url.lower()` **or** (only when `annotation.value` is a `str`)
  a substring of `annotation.value.lower()`. Non-string values are never
  searched.

Counts / stats:

- `count` — a `@property` returning `len(self._annotations)` (call it as
  `store.count`, not `store.count()`).
- `get_stats(self) -> dict` — returns `{"total": self.count, "by_type":
  {type_value: count, ...}, "urls_annotated": len(self._by_url)}`. `by_type`
  is keyed by the **string value** of each `AnnotationType`; `urls_annotated`
  counts the keys in `_by_url` (a URL whose annotations were all removed via
  `remove` still leaves an empty list key, so it can over-count relative to
  `total`).

## Contract Holes

**Primary hole — `add`'s id-collision overwrite desyncs the URL index
(ARCH-42).** The docstring says "Add an annotation to the store," but on an
`annotation_id` collision the body silently does two things the contract never
states:

1. It **overwrites** the existing annotation in `_annotations` with the new
   object (dict assignment) — no merge, no error, no "already exists" signal,
   and the old object's `created_at`/`value`/`metadata` are discarded.
2. It **does not reconcile the URL index**: the new annotation's `url` is
   appended to `_by_url[new_url]`, but the old annotation's `url` still lists
   the same `annotation_id` in `_by_url[old_url]`. So after a collision where
   the new annotation has a *different* URL, `get_by_url(old_url)` returns the
   *new* annotation (whose `url` is `new_url`), and the id is now reachable
   from two URLs while the registry holds only one object. The store's
   invariant "each id maps to exactly one URL" is silently broken.

The fix must make this semantic explicit — either a distinct
`update_annotation`/`upsert` path that preserves `created_at` and reconciles
`_by_url` (removing the id from the old URL's list), or a documented
overwrite default plus a guard that refuses (or warns on) a silent replace and
always keeps `_by_url` consistent with `_annotations` — without changing the
happy-path signature.

Secondary holes (not re-filed here): `to_dict` has no `from_dict` counterpart
and serializes the type under the key `"type"` (not `"annotation_type"`), so
round-tripping is not supported; `get_stats["urls_annotated"]` counts `_by_url`
keys and can over-count after `remove` leaves an empty list; and `search`
never inspects non-string `value`s, so a numeric rating is unsearchable.
