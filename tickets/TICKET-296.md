# TICKET-296: content_search.py SearchIndex.load_index unguarded json.load

- Status: OPEN
- Issue: #421
- Module: personal_index/content_search.py
- Function: SearchIndex.load_index (line 466)

## Symptom
SearchIndex.load_index already degrades to a no-op on non-dict JSON (the `if not isinstance(data, dict): return` guard at line 472), establishing the contract that a malformed index file must NOT crash the loader. However, the `_json.load(f)` read (line 471) is unguarded: a corrupt/truncated index file (e.g. `{`) raises an opaque `json.JSONDecodeError`, violating that degrade-to-no-op contract.

## Evidence
- Line 471: `data = _json.load(f)` in SearchIndex.load_index — no try/except
- Line 472: existing non-dict guard proves the intended degrade value is a no-op (return), not an exception.
- Verified by running the code: writing `{` to an index file makes `SearchIndex().load_index(path)` raise `json.JSONDecodeError`, while writing `[1,2,3]` (non-dict) correctly returns without raising.
- Existing tests (tests/test_content_search.py TestSearchIndexLoadNonDictGuard test_load_null_json / test_load_list_json / test_load_number_json) cover only non-dict JSON, not corrupt JSON.

## Minimal additive fix
Wrap the `_json.load(f)` read in `try/except json.JSONDecodeError: return`, matching the existing non-dict degrade path. Do NOT broaden the docstring — the contract is degrade-to-no-op. Add 1 regression test (corrupt JSON `{` returns without raising).
