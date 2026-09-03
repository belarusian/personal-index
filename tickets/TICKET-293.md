# TICKET-293: url_history.py URLHistory.load unguarded json.load

- Status: OPEN
- Issue: #417
- Module: personal_index/url_history.py
- Function: URLHistory.load (line 153)

## Symptom
URLHistory.load already degrades to 0 on non-list JSON (the `if not isinstance(data, list): return 0` guard at line 160), establishing the contract that a malformed history file must NOT crash the loader. However, the `json.load(f)` read (line 159) is unguarded: a corrupt/truncated history file (e.g. `{`) raises an opaque `json.JSONDecodeError`, violating that degrade-to-zero contract.

## Evidence
- Line 159: `data = json.load(f)` in URLHistory.load — no try/except
- Line 160: existing non-list guard proves the intended degrade value is 0 (return 0), not an exception.
- Verified by running the code: writing `{` to a history file makes `URLHistory().load(path)` raise `json.JSONDecodeError`, while writing `[1,2,3]` (non-list) correctly returns 0.
- Existing tests (tests/test_url_history.py test_load_null_returns_zero / test_load_number_returns_zero / test_load_dict_returns_zero) cover only non-list JSON, not corrupt JSON.

## Minimal additive fix
Wrap the `json.load(f)` read in `try/except json.JSONDecodeError: return 0`, matching the existing non-list degrade path. Do NOT broaden the docstring — the contract is degrade-to-zero. Add 1 regression test (corrupt JSON `{` returns 0).
