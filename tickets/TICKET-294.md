# TICKET-294: progress.py ProgressStore.load_all unguarded json.load

- Status: OPEN
- Issue: #419
- Module: personal_index/progress.py
- Function: ProgressStore.load_all (line 263)

## Symptom
ProgressStore.load_all already degrades to 0 on non-dict JSON (the `if not isinstance(data, dict): return 0` guard at line 272), establishing the contract that a malformed progress file must NOT crash the loader. However, the `json.load(f)` read (line 271) is unguarded: a corrupt/truncated progress file (e.g. `{`) raises an opaque `json.JSONDecodeError`, violating that degrade-to-zero contract.

## Evidence
- Line 271: `data = json.load(f)` in ProgressStore.load_all — no try/except
- Line 272: existing non-dict guard proves the intended degrade value is 0 (return 0), not an exception.
- Verified by running the code: writing `{` to a progress file makes `ProgressStore(storage_path=path).load_all()` raise `json.JSONDecodeError`, while writing `[1,2,3]` (non-dict) correctly returns 0.
- Existing tests (tests/test_progress.py test_load_all_null_json / test_load_all_list_json / test_load_all_number_json) cover only non-dict JSON, not corrupt JSON.

## Minimal additive fix
Wrap the `json.load(f)` read in `try/except json.JSONDecodeError: return 0`, matching the existing non-dict degrade path. Do NOT broaden the docstring — the contract is degrade-to-zero. Add 1 regression test (corrupt JSON `{` returns 0).
