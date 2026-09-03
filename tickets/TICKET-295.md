# TICKET-295: bookmarks.py BookmarkManager.load unguarded json.load

- Status: OPEN
- Issue: #420
- Module: personal_index/bookmarks.py
- Function: BookmarkManager.load (line 148)

## Symptom
BookmarkManager.load already degrades to 0 on non-list JSON (the `if not isinstance(data, list): return 0` guard at line 160), establishing the contract that a malformed bookmarks file must NOT crash the loader. However, the `json.load(f)` read (line 157) is unguarded: a corrupt/truncated bookmarks file (e.g. `{`) raises an opaque `json.JSONDecodeError`, violating that degrade-to-zero contract.

## Evidence
- Line 157: `data = json.load(f)` in BookmarkManager.load — no try/except
- Line 160: existing non-list guard proves the intended degrade value is 0 (return 0), not an exception.
- Verified by running the code: writing `{` to a bookmarks file makes `BookmarkManager(storage_path=path).load(path)` raise `json.JSONDecodeError`, while writing `[1,2,3]` (non-list) correctly returns 0.
- Existing tests (tests/test_bookmarks.py test_load_null_json / test_load_dict_json / test_load_number_json) cover only non-list JSON, not corrupt JSON.

## Minimal additive fix
Wrap the `json.load(f)` read in `try/except json.JSONDecodeError: return 0`, matching the existing non-list degrade path. Do NOT broaden the docstring — the contract is degrade-to-zero. Add 1 regression test (corrupt JSON `{` returns 0).
