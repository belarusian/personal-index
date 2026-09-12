# content-versioning — Exact Contract

Module: `personal_index/content_versioning.py` (250 lines)

Content versioning for tracking and managing versions of content items.
Three public types: `ContentVersion` (a 5-field `@dataclass` with a
`__post_init__` timestamp stamp), `ContentVersioning` (the JSON-file-backed
engine: `create_version`, `get_versions`, `get_version`, `delete_version`,
`rollback_to`, `clear_versions` plus private `_load`/`_save`), and two
module-level convenience functions (`create_version`, `get_versions`) that
delegate to a lazily-created default instance. State lives in a single
`versions.json` file (default `~/.personal_index/versions.json`); there is no
in-memory cache beyond the `_versions` dict that is reloaded from that file on
every construction.

## Public API

### ContentVersion

`@dataclass` with 5 fields:

- `version_id: str`
- `content: str`
- `created_at: str = ""`
- `author: str = ""`
- `message: str = ""`

`__post_init__(self) -> None`: if `self.created_at` is falsy (empty string),
stamps it with `datetime.now(timezone.utc).isoformat()`. A caller-supplied
non-empty `created_at` is preserved verbatim (no parsing, no validation, no
reformatting).

### ContentVersioning

Plain class (not a dataclass). `__init__(self, storage_path: str | None =
None)`:

- `self.storage_path = storage_path or str(Path.home() / ".personal_index" /
  "versions.json")` — a `None` (or empty) `storage_path` falls back to the
  default home path.
- `self._versions: dict[str, list[ContentVersion]] = {}` — keyed by `item_id`,
  each value the ordered list of that item's versions.
- `self._load()` is called immediately, so a fresh instance reflects whatever
  is already on disk.

Private persistence (documented here because the public methods' durability
contract depends on their exact behavior):

- `_load(self) -> None`:
  - if `self.storage_path` does not exist on disk → `self._versions = {}` and
    return (a missing file is a clean empty state, not an error).
  - otherwise reads the file with `json.load`. If the top-level value is not a
    `dict` → `self._versions = {}` and return.
  - otherwise rebuilds `self._versions` by iterating `data.items()`; each
    version is reconstructed as `ContentVersion(version_id=v["version_id"],
    content=v["content"], created_at=v.get("created_at", ""),
    author=v.get("author", ""), message=v.get("message", ""))`. Note
    `version_id` and `content` are read with `[]` (a missing key raises
    `KeyError`), while the other three use `.get(..., "")`.
  - **any** of `json.JSONDecodeError`, `KeyError`, `TypeError` during the read
    → `self._versions = {}` (the whole store is silently cleared, no exception
    propagates, no log, no backup). Under the Option A contract (atomic
    temp-file-and-rename in `_save`), an interrupted `_save` never leaves a
    truncated intermediate on disk, so a corrupt file can only arise from
    pre-existing corruption or an external writer — not from a crashed write.
- `_save(self) -> None` — **atomic write (Option A durability contract)**:
  - `Path(self.storage_path).parent.mkdir(parents=True, exist_ok=True)` (the
    parent directory is created if absent).
  - serializes `self._versions` to a nested dict and writes it to a temp
    file in the same directory (`self.storage_path + ".tmp"`) with
    `json.dump(data, f, indent=2)`, then `f.flush()` + `os.fsync(f.fileno())`,
    then `os.replace(tmp_path, self.storage_path)`. The rename is atomic on
    POSIX, so an interrupted `_save` leaves either the old complete file or
    the new complete file — never a truncated intermediate. Postcondition:
    an interrupted `_save` must NOT leave the store in a state where the
    next construction + mutation silently and permanently loses all prior
    versions.

Public methods:

- `create_version(self, item_id: str, content: str, author: str = "",
  message: str = "") -> ContentVersion` — appends a new version for `item_id`:
  - version numbering is **per-item**: it scans the item's existing versions
    for ids starting with the prefix `f"{item_id}_v"` whose tail is all digits
    (`tail.isdigit()`), takes the max suffix, and sets
    `version_id = f"{item_id}_v{max_suffix + 1}"`. The first version is
    `f"{item_id}_v1"`. A version id whose tail is not all digits (e.g.
    `item_v1b`) is ignored in the max computation.
  - builds `ContentVersion(version_id=..., content=content, author=author,
    message=message)` (so `created_at` is stamped by `__post_init__`), appends
    it to `self._versions[item_id]` (creating the list if the item is new),
    calls `self._save()`, and returns the new `ContentVersion`.
  - it never raises on a normal call; `content` is stored verbatim (no
    empty-content guard, no length cap).

- `get_versions(self, item_id: str) -> list[ContentVersion]` — returns
  `self._versions.get(item_id, [])`: the item's versions in creation order, or
  an empty list if the item has none. Returns the live list (not a copy).

- `get_version(self, item_id: str, version_id: str) -> ContentVersion | None`
  — linear scan of the item's versions for an exact `version_id` match; returns
  the `ContentVersion` on the first match, `None` if the item is absent or no
  version has that id.

- `delete_version(self, item_id: str, version_id: str) -> bool` — if the item
  exists, filters out the matching `version_id`; if the list shrank, calls
  `self._save()` and returns `True`. Returns `False` if the item is absent or
  no version matched (no save in that case). Note: deleting the last version of
  an item leaves an **empty list** under that `item_id` key (the key is not
  removed), so `get_versions` returns `[]` but the item still "exists" in
  `_versions`.

- `rollback_to(self, item_id: str, version_id: str) -> bool` — looks up the
  target version with `get_version`; if `None`, returns `False`. Otherwise it
  does NOT restore in place: it calls `create_version(item_id,
  content=target.content, author=target.author, message=f"rollback to
  {version_id}")` and returns `True` (the `is not None` check is always true,
  since `create_version` always returns a `ContentVersion`). So a "rollback"
  appends a **new** version carrying the old content/author and a
  `rollback to <version_id>` message; the version history only ever grows and
  there is no pointer to a "current" version.

- `clear_versions(self, item_id: str) -> bool` — if the item exists, deletes
  the whole `item_id` key, calls `self._save()`, and returns `True`; returns
  `False` if the item is absent.

### Module-level convenience functions

- `_default_versioning: ContentVersioning | None = None` (module global) and
  `_get_default_versioning() -> ContentVersioning` — lazily creates a single
  default `ContentVersioning()` (using the default home storage path) on first
  call and reuses it thereafter.
- `create_version(item_id: str, content: str, author: str = "", message: str =
  "") -> ContentVersion` — delegates to
  `_get_default_versioning().create_version(...)`.
- `get_versions(item_id: str) -> list[ContentVersion]` — delegates to
  `_get_default_versioning().get_versions(...)`.

These two are the ONLY public module-level entry points: `get_version`,
`delete_version`, `rollback_to`, and `clear_versions` are reachable only via a
caller-constructed `ContentVersioning` instance, not through the default
instance.

## Contract Holes

**Primary hole — non-atomic `_save` + silent-clear `_load` destroy the whole
store on an interrupted write (ARCH-46).** The persistence pair has no
durability guarantee:

- `_save` writes `versions.json` with a **direct** `open(path, "w")` — the file
  is truncated and rewritten in place, with no temp-file-and-rename, no fsync,
  and no backup of the previous contents. If the process is interrupted
  (crash, OOM, power loss) mid-write, `versions.json` is left truncated or
  partially written — i.e. invalid JSON.
- `_load` then catches `json.JSONDecodeError` (and `KeyError`/`TypeError`) and
  sets `self._versions = {}` **silently** — no exception, no log, no signal.
  So the next construction after an interrupted write loads an empty store and
  the very next `_save` (from any `create_version`/`delete_version`/
  `rollback_to`/`clear_versions`) overwrites the corrupt file with the now-empty
  dict, **permanently destroying every version for every item** with no
  indication that data was lost.

This is the same persistence-atomicity class already ticketed for
`personal_index/storage.py` (ARCH-40: `_write_json`/`_read_json`) and
`personal_index/content_pin.py` (ARCH-44: `_save`/`_load`), and it is the
single most important hole here because versioning's entire purpose is
durability — a version store that silently loses all history on a crash defeats
the subsystem. **Option A (atomic write) is implemented:** `_save` now writes
to a temp file in the same directory and `os.replace` it over `versions.json`
(atomic on POSIX), so an interrupted write leaves the previous complete file
intact; `_load`'s missing-file → empty behavior is preserved. The durability
contract is stated in the `_save`/`_load` docstrings and in this page.

Alternative Option B (corruption-detectable load) was considered but not
chosen; the atomic-write pattern matches ARCH-44 and provides the stronger
durability guarantee without changing the load semantics for normal operation.

## Secondary notes (not ticketed)

- **Unbounded retention / no eviction policy.** There is no cap on the number
  of versions per item or on total file size; every `create_version` (and every
  `rollback_to`, which appends a new version) grows the list, and `_save`
  rewrites the **entire** file on every mutation (O(total versions) per write).
  The contract never states a retention/eviction policy, so a long-lived item
  accumulates versions indefinitely.
- **No "current version" pointer; rollback is append-only.** `rollback_to`
  never restores a version in place and there is no field marking which version
  is "current" or "live". The history is a monotonic append log; a caller
  cannot ask "what is the current content of item X" without knowing the
  highest version id, and a "rollback" leaves the newer (post-rollback) version
  as the last entry. The name `rollback_to` over-promises a restore semantic
  the body does not implement.
- **Module-level surface is asymmetric.** Only `create_version` and
  `get_versions` are exposed at module level; `get_version`, `delete_version`,
  `rollback_to`, and `clear_versions` require constructing a
  `ContentVersioning` instance. A caller using the convenience functions cannot
  delete, roll back, or clear without dropping to the instance API.
- **`delete_version` leaves an empty-list key.** Deleting the last version of an
  item leaves `item_id` mapped to `[]` (the key is not removed), so the item
  still "exists" in `_versions` even though it has no versions; only
  `clear_versions` removes the key.
- **`get_versions` returns the live list.** It returns the internal list by
  reference (not a copy), so a caller can mutate the returned list and corrupt
  `_versions` without going through the API.
