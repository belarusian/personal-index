# ARCH-104 — ScheduleStore._save is non-atomic: an interrupted save permanently loses all schedule entries

- **Status:** VERIFIED (validator cycle 271 @ main 76e12b6; _save atomic: tmp+fsync+os.replace at scheduler.py:117-121; pinning tests tests/test_scheduler.py 29 passed; adversarial: no .tmp leftover after add; [was IMPLEMENTED #1580@22a0f46])
- **Kind:** ARCH (architect-authored contract; implementer claims/implements; validator verifies; architect closes)
- **Component:** `personal_index/scheduler.py` — `ScheduleStore._save` (line 108) + `ScheduleStore._load` (lines 52-87)
- **Issue:** #1507

## Symptom

`ScheduleStore._save` writes the schedule file **non-atomically**. It opens the
target file directly with `open(self.path, "w")` (line 108), which truncates the
existing file at open time, and only then `json.dump`s the new contents. If the
process is interrupted (crash, OOM-kill, power loss, `KeyboardInterrupt`)
between the truncate and the completed write, the file is left truncated or
empty.

Because `_load` (lines 52-87) treats ANY corrupt / non-dict / unparseable file
as "reset to empty" (the `except (json.JSONDecodeError, KeyError, TypeError,
ValueError): self._entries = {}` at lines 86-87), the next construction of
`ScheduleStore(path=...)` silently loads an EMPTY store. The user's schedule
entries are gone with no warning, no backup, and no way to recover them.

This is a data-loss hole, not a cosmetic one: `ScheduleStore` is the sole
persistence for scheduled crawl jobs, and every mutating CLI command
(`add`/`remove`/`update` at `cli.py:1105/1149/1186/1201/1236`) calls `_save`.

## Evidence (file:line)

- `personal_index/scheduler.py:108` — `with open(self.path, "w") as f:` inside
  `_save`; the file is truncated at open, before `json.dump` (line 109) runs.
- `personal_index/scheduler.py:109` — `json.dump(data, f, indent=2)` — the
  write happens after the truncate; a crash in this window leaves a partial file.
- `personal_index/scheduler.py:86-87` —
  `except (json.JSONDecodeError, KeyError, TypeError, ValueError):`
  `self._entries = {}` — a truncated/partial JSON file is caught here and the
  store silently resets to empty (no log, no exception, no backup).
- `personal_index/scheduler.py:52-61` — the same silent-empty reset for the
  absent-file and non-dict cases (intentional, pinned by tests).
- `personal_index/cli.py:1105,1149,1186,1201,1236` — every schedule CLI command
  constructs `ScheduleStore(path=store_path)` and mutates it, so each command
  performs a non-atomic `_save`.
- No backup file is ever written: `grep -rn 'backup\|\.bak\|tmp\|rename\|atomic'
  personal_index/scheduler.py` returns nothing.

## Proposed fix (implementer)

Make `_save` atomic using the write-to-temp-then-rename pattern:

1. Write the JSON to a temporary file in the SAME directory as `self.path`
   (e.g. `Path(self.path).with_suffix(".tmp")` or `tempfile.NamedTemporaryFile`
   in the parent dir), `f.flush()` + `os.fsync(f.fileno())`.
2. `os.replace(tmp_path, self.path)` — atomic on POSIX; the target file is
   either the old complete contents or the new complete contents, never a
   partial file.
3. Keep the existing `parent.mkdir(parents=True, exist_ok=True)` (line 104).

The `_load` silent-empty behavior is a documented, tested design constraint
(`tests/test_scheduler.py::test_null_storage_resets_to_empty`,
`test_corrupt_last_run_degrades_to_empty`,
`test_corrupt_next_run_degrades_to_empty`,
`tests/deep/test_defensive_load_sweep_adversarial.py::test_scheduler_store_non_dict_value_degrades`)
and must NOT be changed — the fix is to make `_save` never produce a corrupt
file in the first place.

## Acceptance criteria

1. `ScheduleStore._save` writes to a temp file in the same directory and
   `os.replace`s it onto `self.path`; the target file is never left in a
   truncated/partial state.
2. After a normal `add`/`remove`/`update`, a fresh `ScheduleStore(path=...)`
   loads the same entries (existing persistence tests still pass).
3. The existing corrupt-file / absent-file / non-dict degradation tests in
   `tests/test_scheduler.py` and `tests/deep/test_defensive_load_sweep_adversarial.py`
   still pass unchanged (the `_load` contract is untouched).

## Pinning tests to add (implementer)

- `tests/test_scheduler.py::test_save_is_atomic_no_partial_file` — monkeypatch
  `json.dump` to raise `OSError` mid-write (simulating a crash); assert that
  the ORIGINAL `self.path` file still contains the previous complete JSON
  (i.e. the temp file was the one being written, and `os.replace` never ran,
  so the target is intact). This pins the atomic-replace contract: a failed
  save must not corrupt the existing file.
- `tests/test_scheduler.py::test_save_roundtrip_after_failed_save` — after the
  failed save above, construct a fresh `ScheduleStore(path=...)` and assert it
  loads the pre-failure entries (not empty), proving the user's data survived
  the interrupted write.

## Docs update (same PR)

`docs/scheduler.md` — the "Known contract holes" bullet for non-atomic `_save`
is resolved by this fix; reword it to state the atomic temp+replace contract
and note the `_load` silent-empty degradation is a separate, intentional,
tested constraint (not a hole).

## Self-review checklist (architect)

- [x] Component named precisely (`ScheduleStore._save` + `_load`).
- [x] Public contract stated (signature, behavior, error paths, guard inputs).
- [x] Evidence with file:line for every claim.
- [x] Proposed fix is minimal and additive (temp+rename; no `_load` change).
- [x] Acceptance criteria are verifiable and do not contradict existing tests.
- [x] Pinning tests named with the guard-path input (the mid-write crash).
- [x] Matching docs/ page update ships in the SAME PR.
- [x] Near-name distinction from `content_scheduler.py` stated in the page header.
