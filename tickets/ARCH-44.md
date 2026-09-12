# ARCH-44: content-pin — _save is non-atomic and _load silently clears on corruption

Status: CLAIMED 2026-09-10
Component: `personal_index/content_pin.py`
Issue: #1124
Refs: ARCH-2 (#983 umbrella)

## Symptom

`ContentPinner._save` (lines 68-80) persists the store with a **direct,
non-atomic** write: `open(self.storage_path, "w")` + `json.dump(data, f,
indent=2)` — no temp-file-and-rename. An interrupted write (disk full, process
killed mid-write, `OSError` partway through `json.dump`) leaves the file
truncated or partially written.

The next `ContentPinner(...)` then runs `_load` (lines 46-66), which on
`json.JSONDecodeError` (or `KeyError`/`TypeError`) **silently resets
`self._pinned = {}`** — destroying every pin with no signal, no backup, and no
way for the caller to tell that a corrupt-but-present file was treated as an
empty store. The contract never states that persistence is non-atomic or that
a corrupt file is treated as empty.

This is the exact class as ARCH-40 (storage `_write_json` non-atomic +
`_read_json` silent default): an interrupted write destroys the whole store
with no signal.

## Public contract (the fix must preserve the happy path)

- `pin` / `unpin` / `is_pinned` / `get_pinned_items` / `clear` keep their
  current signatures and happy-path behavior (including `pin`'s
  overwrite/upsert and `unpin`'s absent-id-returns-`True` no-op).
- The persistence contract must be made explicit (pick one and document it in
  the `_save`/`_load` docstrings + `docs/content-pin.md`):
  - **Option A (atomic write):** `_save` writes to a temp file in the same
    directory and `os.replace` it onto `self.storage_path`, so a crash leaves
    either the old complete file or the new complete file — never a truncated
    one.
  - **Option B (corruption is not silent):** `_load` distinguishes a
    corrupt-but-present file from a missing file — e.g. preserve the corrupt
    bytes (rename to `<path>.corrupt-<ts>`), log/raise, or return a sentinel —
    so an interrupted write is detectable rather than silently cleared to `{}`.
- Whichever option is chosen, the postcondition must hold and be stated:
  after any `_save`, the on-disk file is either the previous complete store or
  the new complete store, and a corrupt file is never silently treated as an
  empty store.

## Acceptance criteria

1. The happy path is unchanged: `pin`/`unpin`/`is_pinned`/`get_pinned_items`/
   `clear` behave exactly as documented in `docs/content-pin.md`.
2. The persistence contract is stated in the `_save` and `_load` docstrings
   and in `docs/content-pin.md` (Option A: atomic temp-file-and-rename; Option
   B: a corrupt-but-present file is detectable, not silently cleared).
3. After a `_save`, the on-disk file is always a complete, valid JSON object
   (no truncated intermediate state observable by a concurrent reader).
4. A corrupt-but-present file is never silently reset to `{}` without a
   signal (per the chosen option).

## Pinning tests to add (tests/test_content_pin.py)

- `test_save_is_atomic_no_truncated_file` — pin an item, then simulate an
  interrupted write (e.g. monkeypatch `json.dump` to raise `OSError` partway,
  or write a truncated file directly); assert the on-disk file is either the
  previous complete store or the new complete store, never a truncated
  intermediate (per Option A), and that a subsequent `_load` does not silently
  clear a previously-valid store.
- `test_load_corrupt_file_is_detectable` — write a corrupt (truncated /
  non-JSON) file to `storage_path`, construct a `ContentPinner`, and assert the
  corrupt-but-present file is detectable (per Option B: a sentinel / log /
  preserved bytes), not silently reset to `{}` with no signal.
- `test_load_missing_file_is_empty` — construct a `ContentPinner` with a
  `storage_path` that does not exist; assert `get_pinned_items() == []` (the
  missing-file guard path, distinct from the corrupt-file path).

## Docs update (same PR)

`docs/content-pin.md` "Contract Holes" section (already authored in this PR)
names this as the primary hole; the implementer must update the `_save` and
`_load` entries in the "Public API" section to state the chosen persistence
contract once implemented.
