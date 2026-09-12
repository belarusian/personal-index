# ARCH-39: bookmarks — `load` silently clears and replaces the in-memory set (no merge mode)

Status: IMPLEMENTED 2026-09-12
Component: `personal_index/bookmarks.py`
Issue: #1110
Refs: ARCH-2 (#983 umbrella)

## Symptom

`BookmarkManager.load` (lines 148-175) does `self._bookmarks.clear()` and
then repopulates from the file. There is no merge/append mode and no way to
distinguish "replaced N loaded bookmarks" from "discarded M unsaved
bookmarks". Any in-memory bookmark that was never `save`d is silently lost
the moment `load` is called — including the common "pick up another
process's file" pattern. The only safe persistence round-trip is
save-then-load, and the API gives no signal that a load destroyed state.

This is the single most important hole in the module: the store's
persistence path has an underspecified replace-vs-merge semantic, and the
default (replace) destroys unsaved work without warning.

## Public contract (target)

`load` gains an explicit merge semantic while keeping replace as the
default (backward compatible):

- `load(self, path: str | None = None, merge: bool = False) -> int`
- `merge=False` (default): current behavior — clear the set, replace with
  the loaded bookmarks, return the count loaded.
- `merge=True`: upsert loaded bookmarks over the current set using the same
  collision rule as `add` (existing `created_at` preserved on URL
  collision, `updated_at` refreshed to now); bookmarks present only in
  memory are kept. Returns the number of bookmarks upserted from the file.
- All existing guard paths are unchanged: `ValueError` when neither `path`
  nor the configured storage path is set; return `0` without touching the
  current set when the file is missing, the JSON is malformed
  (`JSONDecodeError`), or the top-level JSON value is not a list.

## Acceptance criteria

1. `merge=False` (default) with a non-empty in-memory set and a file
   holding different URLs: the in-memory set is replaced exactly by the
   file contents; return value = file count.
2. `merge=True` with overlapping URLs: the existing `created_at` is
   preserved on the collision, `updated_at` is refreshed, and file-only and
   memory-only bookmarks are both present afterwards; return value = number
   of bookmarks read from the file.
3. `merge=True` with a missing file / malformed JSON / non-list top level:
   returns `0` and the in-memory set is untouched (guard path).
4. `load` with neither `path` nor `storage_path` raises `ValueError` in
   both merge modes.

## Pinning tests to add (implementer)

- `test_load_default_replaces_unsaved`: add an unsaved bookmark in memory,
  `load` a file with different URLs (default mode); assert the unsaved
  bookmark is gone, the file's bookmarks are present, and the return value
  equals the file count (pins the replace default).
- `test_load_merge_preserves_and_upserts`: seed memory with bookmark `a`
  (known `created_at`) and bookmark `mem_only`; file holds `a` (changed
  title) and `file_only`; `load(merge=True)`; assert `a` keeps its original
  `created_at` but has the file's title, both `mem_only` and `file_only`
  are present, and the return value is 2 (pins the merge semantic).
- `test_load_merge_missing_file_noop`: non-empty in-memory set;
  `load(path=<missing>, merge=True)`; assert return value 0 and the
  in-memory set is unchanged (guard-path pin alongside the normal case).

## Docs

`docs/bookmarks.md` (authored this cycle) documents the current behavior and
lists this as the primary contract hole. Update the `load` entry and the
"Contract Holes" section in the **same PR** that implements the fix, so the
page reflects the explicit replace/merge semantic.
