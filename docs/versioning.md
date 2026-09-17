# versioning — spec

> **DEAD MODULE — 0 importers.** `personal_index/versioning.py` is never
> imported or registered anywhere in `personal_index/` (witness:
> `grep -rn 'import versioning\|from personal_index.versioning\|from
> .versioning' personal_index/ --include=*.py` returns nothing, rc=1). It is a
> dead parallel implementation. Its only consumer is the test suite
> (`tests/test_versioning.py`).
>
> **NEAR-NAME-COLLISION DISAMBIGUATION.** This page documents
> `personal_index/versioning.py` (the **in-memory, url-keyed** tracker:
> `VersionTracker` + a bare `ContentVersion` dataclass, no persistence). It is
> a DIFFERENT module from `personal_index/content_versioning.py` (the
> **JSON-file-backed, item_id-keyed** engine: `ContentVersioning` +
> `create_version`/`get_versions`/`get_version`/`delete_version`/`rollback_to`/
> `clear_versions` + `_load`/`_save`), which is the live integration and is
> covered by [content-versioning.md](content-versioning.md). The two modules
> share the class name `ContentVersion` and the method name `get_versions` but
> have **divergent, incompatible contracts** — do not conflate them. The live
> twin is `content_versioning`; this module is dead.

## Purpose

A standalone, **in-memory** content-versioning tracker: construct a
`VersionTracker`, call `record_version(url, content, ...)` to append a
snapshot keyed by **url**, and query the in-process history with
`get_versions`/`get_latest`/`has_changed`/`get_change_count`. It keeps
**everything in a process-local `dict`** — there is no persistence (no
`_load`/`_save`/`storage_path`), so **nothing survives a process restart**, and
there is **no `rollback_to` and no `delete_version`**. This is the opposite of
the live twin's model, which persists to a `versions.json` file keyed by
`item_id` and offers rollback + delete-by-id.

## Public API

### `ContentVersion` (dataclass, versioning.py:14)
Fields (7): `url: str`, `version_id: str`, `content_hash: str`,
`title: str = ""`, `content_length: int = 0`,
`captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))`,
`metadata: dict = field(default_factory=dict)`.

- `to_dict()` (versioning.py:25) — returns a **fresh** dict (a new object on
  every call) with exactly the seven fields as keys in declaration order
  (`url`, `version_id`, `content_hash`, `title`, `content_length`,
  `captured_at`, `metadata`). `captured_at` is serialized to an ISO-8601 string
  via `.isoformat()`; all other values are the corresponding field values. The
  `metadata` dict is the **same reference** as `self.metadata` (not copied).
  The method is pure (it does not mutate `self`).

> **Divergence from the live twin.** The live twin's `ContentVersion`
> (content_versioning.py:16) is a 5-field dataclass (`version_id`, `content`,
> `created_at`, `author`, `message`) with a `__post_init__` that stamps
> `created_at`. This module's `ContentVersion` is a 7-field dataclass keyed by
> **url** with a `content_hash`/`content_length`/`metadata` shape and a
> `to_dict()` serializer — a different value object entirely.

### `VersionTracker` (versioning.py:49)
- `__init__(self, max_versions: int = 10)` (versioning.py:52) — sets
  `self._versions: dict[str, list[ContentVersion]] = {}` (keyed by **url**) and
  `self._max_versions = max_versions`. **No `storage_path`, no `_load()` call**
  — the store starts empty in memory and never touches disk.
- `compute_hash(content) -> str` (staticmethod, versioning.py:57) —
  `hashlib.sha256(content.encode("utf-8")).hexdigest()`.
- `generate_version_id(url, hash_value) -> str` (staticmethod,
  versioning.py:62) — `hashlib.sha256(f"{url}:{hash_value}".encode()).hexdigest()[:12]`.
- `record_version(self, url, content, title="", metadata=None) -> ContentVersion`
  (versioning.py:67) — computes the content hash + version id, builds a
  `ContentVersion`, and appends it to `self._versions[url]` (creating the list
  if the url is new). **Dedup guard:** if the url already has a version and the
  last one's `content_hash` equals the new hash, it returns the existing last
  version without appending. **Retention:** if `self._max_versions <= 0` the
  url's list is reset to `[]`; otherwise if the list exceeds `max_versions` it
  is truncated to the last `max_versions` entries. Returns the (new or existing)
  `ContentVersion`.
- `get_versions(self, url) -> list[ContentVersion]` (versioning.py:99) —
  `self._versions.get(url, [])`: the url's versions in record order, or `[]`
  if the url has none. Returns the **live list** (not a copy).
- `get_latest(self, url) -> ContentVersion | None` (versioning.py:103) — the
  last version for the url, or `None` if the url has none.
- `has_changed(self, url, new_content) -> bool` (versioning.py:108) — `True`
  when the url has no latest version; otherwise `True` iff
  `compute_hash(new_content) != latest.content_hash`.
- `get_change_count(self, url) -> int` (versioning.py:116) —
  `len(self._versions.get(url, []))`.
- `get_all_urls(self) -> list[str]` (versioning.py:120) —
  `list(self._versions.keys())`.
- `clear(self, url=None) -> None` (versioning.py:124) — if `url` is truthy,
  pops that url's list; otherwise clears the whole store.
- `total_versions` (property, versioning.py:132) — `sum(len(v) for v in
  self._versions.values())`.
- `tracked_urls` (property, versioning.py:137) — `len(self._versions)`.

## Invariants

1. **In-memory only — no persistence.** The store is a process-local
   `dict[str, list[ContentVersion]]`. There is no `storage_path`, no
   `_load`/`_save`, and no file I/O anywhere in the module. Every version is
   **lost on process exit**; a fresh `VersionTracker()` always starts empty.
2. **Keyed by url, not item_id.** Unlike the live twin (keyed by `item_id`),
   this module's history is indexed by the content **url**.
3. **No rollback, no delete-by-id.** The only removal operations are
   `clear(url)` (drop one url's whole history) and `clear()` (drop everything).
   There is no `rollback_to` and no `delete_version` — a single version cannot
   be removed or restored.
4. **Consecutive-duplicate suppression + bounded retention.** `record_version`
   does not append a version whose hash equals the url's current last hash, and
   each url's list is capped at `max_versions` (default 10); `max_versions <= 0`
   resets the url's list to empty.

## Confirmed contract (ARCH-108)

**ARCH-108 is confirmed (architect, cycle 297): Option (b) — the live twin is
the sole content-versioning contract, and the dead module is marked for
deletion in the IMPL lane (NOT this docs-only pass).**
`personal_index/versioning.py` is a dead parallel implementation (0 importers —
witness: `grep -rn 'import versioning\|from personal_index.versioning\|from
.versioning' personal_index/ --include=*.py` returns nothing, rc=1; its only
consumer is the test suite `tests/test_versioning.py`). The live
content-versioning contract is the JSON-file-backed, **item_id**-keyed
`ContentVersioning` in `content_versioning.py` (covered by
[content-versioning.md](content-versioning.md)); it is the **sole**
content-versioning contract. This module is **not** a substitute for it and is
**marked for deletion** (the implementer deletes it when it claims ARCH-108;
this docs-only pass does not touch the code).

The module's actual, confirmed contract is exactly what the Invariants above
state, and it is **intentionally NOT** the live twin's contract:

- **In-memory only — no persistence.** `VersionTracker` (versioning.py:49) has
  no `storage_path`/`_load`/`_save`; nothing survives a process restart and a
  fresh `VersionTracker()` always starts empty. This is by design for a dead
  module, not a gap to be filled.
- **No `rollback_to` / no `delete_version`.** The only removal operations are
  `clear(url)` and `clear()` (versioning.py:124). A consumer needing persisted
  history, rollback, or delete-by-id must use the live twin `ContentVersioning`
  (content_versioning.py:31), which persists to `versions.json` via
  `_load`/`_save` (content_versioning.py:46/83) and offers `rollback_to`
  (content_versioning.py:195) + `delete_version` (content_versioning.py:174).

**Witness:** the validator's deep test
`tests/deep/test_versioning_adversarial.py` pins this in-memory contract
(`to_dict` seven-key shape, `record_version` dedup/retention, `clear`,
`get_versions`/`get_latest`, and fresh construction starting empty — nothing is
reloaded across constructions) — the corrected docs match the module's observed
behavior. See tickets/ARCH-108.md.
