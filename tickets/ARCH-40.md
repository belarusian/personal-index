# ARCH-40: storage — non-atomic write + silent corruption recovery destroys the store

Status: IMPLEMENTED #1299@cf7180f
Component: `personal_index/storage.py`
Issue: #1113
Refs: ARCH-2 (#983 umbrella)

## Symptom

`Storage._write_json` (lines 41-43) writes directly to the target file with
`filepath.write_text(json.dumps(...))` — no temp-file-and-rename, no fsync,
no backup of the previous contents. An interrupted write (process crash,
disk full, power loss) leaves a **truncated/partial JSON file** on disk.

The next `_read_json` (lines 29-43) then hits `json.JSONDecodeError` and —
with no error, no log, no `.bak` fallback — silently returns the empty
default: `[]` for `interests.json`/`pages.json`, `{}` for `config.json`.
`get_interests`/`get_pages`/`get_config` surface that as an **empty store**.

So the entire persisted dataset is destroyed with no signal to the caller:
a crash mid-`add_page` on a 10,000-page index silently reads back as zero
pages, and a crash mid-`add_interest` silently reads back as zero interests.
This is the single most important hole in the module: the persistence path
has an underspecified atomicity + corruption-recovery semantic, and the
default (silent empty) destroys the whole store without warning.

## Public contract (target)

Make the write atomic and make corruption recovery explicit, while keeping
the public method signatures unchanged (the fix is internal to
`_write_json`/`_read_json`):

- `_write_json`: write to a temp file in the **same directory** as the
  target (e.g. `filepath.with_suffix(filepath.suffix + ".tmp")`), flush +
  `os.fsync`, then `os.replace(tmp, filepath)` (atomic on POSIX). Before the
  replace, copy the existing target to a recoverable backup
  (e.g. `filepath.with_suffix(filepath.suffix + ".bak")`) so a failed write
  can be rolled back.
- `_read_json`: on `json.JSONDecodeError`, **before** returning the empty
  default, attempt to read the `.bak` backup and, if it parses, return the
  backup contents (and surface the corruption — e.g. log a warning). Only
  return the empty default when neither the target nor the backup is
  recoverable. The empty/whitespace guard path (return default) is unchanged.

## Acceptance criteria

1. A normal `add_page`/`add_interest`/`save_config` followed by a read
   round-trips the record exactly (no regression from the atomic write).
2. A write interrupted mid-way (simulated by leaving a truncated target and
   a valid `.bak`) reads back the **backup** contents, not the empty
   default, and the corruption is surfaced (warning/log), not silent.
3. A write interrupted with **no** valid backup (fresh store, truncated
   target) reads back the empty default — the existing guard path.
4. An empty/whitespace file still returns the empty default (unchanged).
5. No `.tmp` file is left behind after a successful write.

## Pinning tests to add (implementer)

- `test_write_atomic_roundtrip`: `add_page` a record, `get_page` it back;
  assert the fields match and no `*.tmp` file remains in `data_dir` (pins
  the atomic-write happy path).
- `test_corrupt_target_recovers_from_backup`: seed a valid store, write a
  valid `.bak`, then truncate the target to invalid JSON; `get_pages()`;
  assert the backup's pages are returned (not `[]`) and a warning is
  emitted (pins the corruption-recovery path).
- `test_corrupt_target_no_backup_returns_default`: truncate the target with
  no `.bak` present; `get_pages()`; assert `[]` is returned (guard-path pin
  alongside the recovery case).

## Docs

`docs/storage.md` (authored this cycle) documents the current behavior and
lists this as the primary contract hole. Update the `_write_json`/
`_read_json` entries and the "Contract Holes" section in the **same PR**
that implements the fix, so the page reflects the atomic-write +
backup-recovery semantic.
