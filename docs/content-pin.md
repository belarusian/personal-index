# content-pin — Exact Contract

Module: `personal_index/content_pin.py` (194 lines)

Content pinning system for marking content items as important / permanently
stored. Two public types: `PinnedItem` (a 4-field `@dataclass` for a single
pinned item) and `ContentPinner` (a JSON-file-backed store keyed by item id,
with `_load`/`_save` persistence and a lazy module-level default singleton).
There is no locking; `ContentPinner` is single-threaded by contract.

## Public API

### PinnedItem

`@dataclass` with fields:

- `item_id: str` — the id of the pinned content item; the store key.
- `pinned_at: str = ""` — an ISO-8601 UTC timestamp string; when left empty
  (the default) `__post_init__` stamps it to the current UTC time.
- `reason: str = ""` — an optional free-text reason for the pin.
- `metadata: dict = field(default_factory=dict)` — an optional metadata dict.

`__post_init__(self) -> None`: if `self.pinned_at` is falsy, set it to
`datetime.now(timezone.utc).isoformat()`.

### ContentPinner

Plain class (not a dataclass). `__init__(self, storage_path: str | None = None)`:

- `self.storage_path` — `storage_path` if given, else
  `str(Path.home() / ".personal_index" / "pinned_items.json")`.
- `self._pinned: dict[str, PinnedItem]` — the primary registry, keyed by
  `item_id`.
- calls `self._load()`.

Methods:

- `_load(self) -> None` — if the file does not exist, set `self._pinned = {}`
  and return. Otherwise `json.load` the file; if the loaded value is not a
  `dict`, set `self._pinned = {}` and return. Otherwise rebuild
  `self._pinned` from scratch: for each `item_id, item_data` in
  `data.items()`, create
  `PinnedItem(item_id=item_id, pinned_at=item_data.get("pinned_at", ""),
  reason=item_data.get("reason", ""), metadata=item_data.get("metadata", {}))`.
  On `json.JSONDecodeError`, `KeyError`, or `TypeError`, set
  `self._pinned = {}` (a silent clear — no signal, no backup).
- `_save(self) -> None` — `mkdir(parents=True, exist_ok=True)` the file's
  parent directory, build
  `data = {item_id: {"pinned_at": ..., "reason": ..., "metadata": ...}}`
  (the `item_id` is the JSON **key**, not a field of the value), then
  `open(self.storage_path, "w")` + `json.dump(data, f, indent=2)`. The write
  is **non-atomic** (direct write, no temp-file-and-rename).
- `pin(self, item_id: str, reason: str = "", metadata: dict | None = None) -> bool`
  — take `snapshot = dict(self._pinned)`, then
  `self._pinned[item_id] = PinnedItem(item_id=item_id, reason=reason,
  metadata=metadata or {})` (**overwrites any existing entry for `item_id`**:
  a fresh `pinned_at`, and `reason`/`metadata` are replaced, not merged).
  Then `self._save()` inside `try/except OSError`; on `OSError` restore
  `self._pinned = snapshot` and return `False`; otherwise return `True`.
- `unpin(self, item_id: str) -> bool` — if `item_id in self._pinned`: take a
  snapshot, `del self._pinned[item_id]`, then `self._save()` inside
  `try/except OSError`; on `OSError` restore the snapshot and return `False`.
  Return `True` in all other cases — including when `item_id` was **not**
  pinned (an absent id is a no-op that still returns `True`).
- `is_pinned(self, item_id: str) -> bool` — `item_id in self._pinned`.
- `get_pinned_items(self) -> list[PinnedItem]` — `list(self._pinned.values())`
  in dict insertion order (not sorted by `pinned_at`).
- `clear(self) -> None` — `self._pinned.clear()` then `self._save()`. Unlike
  `pin`/`unpin`, the `_save()` call is **not** wrapped in `try/except OSError`,
  so a disk I/O error here raises an uncaught `OSError`; returns `None`.

### Module-level functions

- `_default_pinner: ContentPinner | None = None` — module global, `None` until
  first use.
- `_get_default_pinner() -> ContentPinner` — lazy singleton: create
  `ContentPinner()` (default path) on first call, cache and return it.
- `pin_content(item_id: str, reason: str = "", metadata: dict | None = None) -> bool`
  — `_get_default_pinner().pin(item_id, reason, metadata)`.
- `unpin_content(item_id: str) -> bool` — `_get_default_pinner().unpin(item_id)`.

## Contract Holes

**Primary hole — `_save` is non-atomic and `_load` silently clears on
corruption (ARCH-44).** `_save` writes the store with a direct
`open(self.storage_path, "w")` + `json.dump` — no temp-file-and-rename. An
interrupted write (disk full, process killed mid-write) leaves the file
truncated or partially written. The next `ContentPinner(...)` `_load` then
hits `json.JSONDecodeError` and **silently resets `self._pinned = {}`** —
destroying every pin with no signal and no backup. The contract never states
that persistence is non-atomic or that a corrupt-but-present file is treated
as an empty store. This is the exact class as ARCH-40 (storage `_write_json`
non-atomic + `_read_json` silent default): an interrupted write destroys the
whole store with no signal.

## Secondary notes (not ticketed)

- `pin` re-pin is an **overwrite/upsert**, not a merge: re-pinning an already
  pinned id replaces `reason` and `metadata` and stamps a fresh `pinned_at`.
  Reasonable, but the contract never states it.
- `unpin` on an absent id returns `True` (a no-op) — documented in the
  docstring ("or was not pinned"), not a hole.
- `clear()` calls `_save()` without the `try/except OSError` rollback that
  `pin`/`unpin` have, so an I/O error in `clear()` raises an uncaught
  `OSError` (inconsistent error contract).
- `_load` on a persisted item whose `pinned_at` is missing/empty lets
  `__post_init__` stamp a **fresh** UTC timestamp, so a pin that lost its
  timestamp on disk is silently re-dated to load time.
- `_load`'s `except` clause catches `JSONDecodeError`/`KeyError`/`TypeError`
  but not `AttributeError`; a malformed item value that is not a `dict`
  (e.g. a string) makes `item_data.get(...)` raise an uncaught
  `AttributeError` during load.
