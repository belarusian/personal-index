# ARCH-46: content-versioning — non-atomic _save + silent-clear _load destroy the whole store on an interrupted write

Status: CLAIMED 2026-09-12
Component: `personal_index/content_versioning.py`
Issue: #1131
Refs: ARCH-2 (#983 umbrella); same persistence-atomicity class as ARCH-40 (storage) and ARCH-44 (content-pin)

## Symptom

The persistence pair `_save`/`_load` has no durability guarantee, and the
failure mode is total, silent data loss:

- `_save` (lines 72-90) writes `versions.json` with a **direct**
  `open(self.storage_path, "w")` — the file is truncated and rewritten in
  place, with no temp-file-and-rename, no fsync, and no backup of the previous
  contents. If the process is interrupted (crash, OOM, power loss) mid-write,
  `versions.json` is left truncated or partially written — i.e. invalid JSON.
- `_load` (lines 46-70) catches `json.JSONDecodeError` (and `KeyError`/
  `TypeError`) and sets `self._versions = {}` **silently** — no exception, no
  log, no signal. So the next construction after an interrupted write loads an
  empty store, and the very next `_save` (from any `create_version`/
  `delete_version`/`rollback_to`/`clear_versions`) overwrites the corrupt file
  with the now-empty dict, **permanently destroying every version for every
  item** with no indication that data was lost.

This is the same persistence-atomicity class already ticketed for
`personal_index/storage.py` (ARCH-40: `_write_json`/`_read_json`) and
`personal_index/content_pin.py` (ARCH-44: `_save`/`_load`). It is the single
most important hole in this module because versioning's entire purpose is
durability — a version store that silently loses all history on a crash defeats
the subsystem.

## Public contract (the fix must preserve the happy path)

- All six public methods keep their current signatures and behavior:
  `create_version` (per-item `f"{item_id}_v{n}"` numbering, appends, saves,
  returns the new `ContentVersion`), `get_versions` (creation order, `[]` for
  absent items), `get_version` (exact-id match, `None` if absent),
  `delete_version` (`True`/`False`, leaves an empty-list key when the last
  version is removed), `rollback_to` (appends a new version carrying the target
  content/author + a `rollback to <version_id>` message; `False` if the target
  is absent), `clear_versions` (removes the `item_id` key; `True`/`False`).
- `_load`'s missing-file → empty behavior is preserved (a fresh store with no
  file is a clean empty state, not an error).
- The persistence durability contract must be made explicit (pick one and
  document it in the `_save`/`_load` docstrings + `docs/content-versioning.md`):
  - **Option A (atomic write):** make `_save` write to a temp file in the same
    directory and `os.replace` it over `versions.json` (atomic on POSIX), so an
    interrupted write leaves the previous complete file intact.
  - **Option B (corruption-detectable load):** keep the direct write but make
    `_load` distinguish "file absent" (clean empty) from "file present but
    unparseable" (corruption) — e.g. raise a typed error or log + preserve a
    backup — so a corrupt file is surfaced instead of silently cleared to `{}`.
- Whichever option is chosen, the postcondition must hold and be stated: an
  interrupted `_save` must NOT leave the store in a state where the next
  construction + mutation silently and permanently loses all prior versions.

## Acceptance criteria

1. The happy path is unchanged: all six public methods behave exactly as
   documented in `docs/content-versioning.md`.
2. A fresh store with no `versions.json` still loads as an empty store (no
   error).
3. The durability contract is stated in the `_save`/`_load` docstrings and in
   `docs/content-versioning.md` (Option A: atomic temp-file-and-rename; Option
   B: corruption is surfaced, not silently cleared).
4. After simulating an interrupted/corrupt `versions.json`, the next
   construction does NOT silently clear the store to `{}` and then overwrite
   the file with the empty dict (Option A: the previous complete file is
   intact; Option B: the corruption is raised/logged, not swallowed).

## Pinning tests to add (tests/test_content_versioning.py)

- `test_create_version_numbering` — pin the per-item `f"{item_id}_v{n}"`
  numbering: first version is `f"{item_id}_v1"`, second is `_v2`, and a version
  id whose tail is not all digits (e.g. `f"{item_id}_v1b"`) is ignored in the
  max computation (the next real version is still `_v2`, not `_v1b+1`).
- `test_load_missing_file_is_empty` (guard path) — construct a
  `ContentVersioning` with a `storage_path` that does not exist and assert
  `get_versions` returns `[]` (the missing-file → empty guard, no exception).
- `test_save_load_roundtrip` — create versions, construct a fresh instance from
  the same `storage_path`, and assert the versions survive (content, author,
  message, created_at) — pins the happy-path persistence.
- `test_interrupted_write_does_not_silently_destroy` (the contract hole) —
  write a valid `versions.json` with known versions, then corrupt it (truncate
  to invalid JSON), construct a fresh instance, and assert the documented
  durability behavior: Option A → the previous complete file is intact (or the
  corrupt file is not overwritten with `{}`); Option B → the corruption is
  raised/logged rather than silently cleared to `{}`. This single test pins the
  whole contract hole.

## Docs update (same PR)

`docs/content-versioning.md` "Contract Holes" section (already authored in this
PR) names this as the primary hole; the implementer must update the `_save` and
`_load` entries in the "Public API" section to state the chosen durability
contract once implemented.
