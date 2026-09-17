# ARCH-71 — search_index: `_save` is non-atomic and unflushed, so a crash mid-write truncates the index and the next `_load` silently loses all data

Status: CLOSED (architect close, cycle 280; verified by validator) #1424@6834ed3 (validator cycle 225: 4 AC pins + 5 adversarial deep tests green, tests/deep/test_search_index_atomic_save_adversarial.py)
Component: `personal_index/search_index.py` — `SearchIndex._save` (lines 52-74); the degrade half `SearchIndex._load` (lines 32-51); the divergent durable counterpart `personal_index/index.py::SearchIndex._save` (lines 62-76)
Umbrella: ARCH-2 (#983)
Issue: #1403
Docs: `docs/search_index.md` (Contract Hole 1)

## Problem
`SearchIndex._save` (line 52) persists the index with:

    with open(self.index_path, "w") as f:
        json.dump(data, f, indent=2)

This has two durability defects:

1. **Non-atomic write.** `open(..., "w")` truncates the existing file to zero
   bytes *before* any byte is written. If the process is killed, the disk
   fills, or the write is otherwise interrupted between the truncation and the
   completion of `json.dump`, the file on disk is left **empty or partial** —
   a truncated JSON document. Because `add` (line 75), `remove` (line 87), and
   `clear` (line 111) all call `_save` on every mutation, a single interrupted
   write destroys the entire persisted index.
2. **No flush / no fsync.** The body never calls `f.flush()` or
   `os.fsync(f.fileno())`, so even a completed `json.dump` is not guaranteed to
   reach stable storage before the process exits.

The consequence is **silent total data loss**: the next
`SearchIndex(index_path)` construction runs `_load` (line 32), which hits
`json.JSONDecodeError` on the truncated file and **resets both `_pages` and
`_word_index` to `{}`** (the defensive degrade, lines 49-51). The caller sees
an empty index with no error, no log, and no signal that data was lost.

The covered sibling module `personal_index.index.SearchIndex._save`
(`docs/search-index.md`) does the opposite: it calls `f.flush()` and
`os.fsync(f.fileno())` after `json.dump`. The two `SearchIndex` classes in this
package therefore have **divergent durability guarantees** for the same
"persist the index" operation. This is the same "advertised safety not actually
provided" class as ARCH-66/67/68/69/70: the docstring "Save index to file."
implies a durable save, but the body provides neither durability (flush/fsync)
nor atomicity (temp-file + rename).

## Public contract (target)
`_save` must persist the index **atomically and durably**, so that a crash at
any point during a save leaves the on-disk file either the previous complete
index or the new complete index — never a truncated/partial file.

1. Reword the `_save` docstring (line 53) to state the exact durability
   contract: the index is written to a temp file in the same directory,
   flushed and fsynced, then atomically replaced over `index_path` via
   `os.replace`; a crash mid-write leaves the prior complete file intact.
2. Change the body to write atomically + durably, e.g.:
       parent = Path(self.index_path).parent
       parent.mkdir(parents=True, exist_ok=True)
       data = {"pages": pages_data, "word_index": self._word_index}
       tmp = self.index_path + ".tmp"
       with open(tmp, "w") as f:
           json.dump(data, f, indent=2)
           f.flush()
           os.fsync(f.fileno())
       os.replace(tmp, self.index_path)
   (The temp-file name must be in the **same directory** as `index_path` so
   `os.replace` is an atomic same-filesystem rename. The 11-key page
   serialization and the `data` shape are unchanged.)
3. Add ONE pinning test that exercises the real `_save` entry point and asserts
   the on-disk file is a complete, re-loadable index after a save (see Pinning
   tests).
4. The `_load` degrade-to-empty behavior on genuinely corrupt/non-dict input
   must remain **unchanged** — it is pinned by
   `tests/deep/test_defensive_load_sweep_adversarial.py` (Site 2) and is the
   *consequence* half of this hole, not the cause.

## Behavior
- `_save()` on a normal index: writes a complete, valid JSON document to
  `index_path`; a subsequent `SearchIndex(index_path)` reloads the full index
  (all pages + word index). **Unchanged** in the happy path.
- `_save()` interrupted mid-write (simulated by writing a truncated file):
  **after the fix**, this scenario cannot arise from `_save` itself because the
  write is atomic — the on-disk file is always either the prior complete index
  or the new complete index. (The pinning test simulates the *pre-fix* failure
  mode to witness the contract, see below.)
- `_load()` on a genuinely corrupt file (written by something other than
  `_save`): **unchanged** — degrades to `{}` (pinned by the deep test).
- `add` / `remove` / `clear`: **unchanged** — they still call `_save` and the
  in-memory state transitions are identical; only the persistence mechanism
  changes.

## Guard inputs
- **Empty index save:** `SearchIndex(path)` with no pages, then `_save()` →
  the on-disk file is `{"pages": {}, "word_index": {}}` (a complete, valid,
  re-loadable document) — the guard path for the pinning test.
- **Missing parent dir:** `index_path` in a not-yet-existing directory →
  `_save` still creates the parent (`mkdir(parents=True, exist_ok=True)`) and
  writes the file (regression guard — the current body already does this and
  must keep doing so).
- **Crash-mid-write simulation:** a file pre-written with a truncated JSON
  prefix (e.g. `{"pages": {"http://x": {"url": "http://x", "tit`) → a fresh
  `SearchIndex(path)` degrades to an empty index (this pins the *consequence*
  half and must remain true; it is the input the atomic `_save` is designed to
  never produce).

## Acceptance criteria
1. After `idx.add(page)` (or any mutation that calls `_save`), the on-disk file
   at `index_path` is a **complete, valid JSON document** that a fresh
   `SearchIndex(index_path)` reloads to the same page set and word index.
2. `_save` writes to a temp file in the same directory and calls
   `os.replace(tmp, self.index_path)` — the on-disk `index_path` is never left
   truncated by `_save` itself (witnessed by the pinning test that the file is
   always re-loadable after a save).
3. `_save` calls `f.flush()` and `os.fsync(f.fileno())` before the replace
   (durability, matching the covered sibling `personal_index.index._save`).
4. The `_load` degrade-to-empty behavior on a genuinely corrupt file is
   **unchanged** — the existing deep test
   `tests/deep/test_defensive_load_sweep_adversarial.py` (Site 2) still passes
   without modification.
5. The `_save` docstring states the exact atomic + durable contract (temp file
   in the same directory, flush + fsync, `os.replace`) and no longer implies a
   plain in-place `open(..., "w")` write.
6. The 11-key page serialization and the `{"pages": ..., "word_index": ...}`
   document shape are unchanged (no change to the persisted schema).

## Pinning tests to add
- `test_save_produces_complete_reloadable_file` (the durability pin): add one
  page to a `SearchIndex` backed by a `tmp_path` file; assert the on-disk file
  exists, `json.load` succeeds on it, and a **fresh** `SearchIndex(same_path)`
  reloads to `count() == 1` with the same url and a matching word index. This
  exercises the real `_save` entry point and pins the "always complete"
  contract against the returned/reloaded object, not the docstring wording.
- `test_save_empty_index_writes_valid_document` (guard path): a fresh
  `SearchIndex(tmp_path)` with no pages, then `_save()`; assert the on-disk
  file is `{"pages": {}, "word_index": {}}` (a complete, valid, re-loadable
  document) — the empty-index guard.
- `test_save_creates_missing_parent_dir` (regression guard): `index_path` in a
  not-yet-existing nested directory; `_save()`; assert the file exists and
  re-loads — the `mkdir(parents=True, exist_ok=True)` behavior is preserved.
- `test_load_corrupt_file_still_degrades_to_empty` (consequence-half pin,
  must remain true): pre-write a truncated JSON prefix to the file, construct
  `SearchIndex(path)`, assert `count() == 0` and `urls() == []`. This is the
  input the atomic `_save` is designed to never produce; it pins that the
  `_load` defensive degrade is unchanged.
- **Do NOT modify** the existing deep test
  `tests/deep/test_defensive_load_sweep_adversarial.py` (Site 2) or
  `tests/test_search_index.py` — they pin the `_load` degrade and the current
  happy-path behavior, both of which remain correct after the fix.

## Follow-up

- Cycle 284 (architect): reconciled the stale `docs/search_index.md` Hole 1 "Fix direction (implementer)" callout to the confirmed atomic/durable contract (ARCH-71, verified cycle 225); the open fix-choice block was replaced with a one-line confirmed-fix note naming the pinning tests. Docs-only; no code or test change.

- Cycle 308 (architect): reconciled the stale `docs/README.md` index line for `search_index.md` to the confirmed atomic/durable `_save` contract (ARCH-71, verified cycle 225); the "(ARCH-71) contract hole" framing was restated to the confirmed contract. Docs-only; no code or test change.
