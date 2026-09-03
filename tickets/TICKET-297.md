# TICKET-297: analytics.py AnalyticsTracker.load unguarded json.load

- Status: RESOLVED (merged to main, gh #424 closed)
- Issue: #424
- Module: personal_index/analytics.py
- Function: AnalyticsTracker.load (line 275)

## Symptom
AnalyticsTracker.load already degrades to 0 on non-dict JSON (the `if not isinstance(data, dict): return 0` guard at line 278), establishing the contract that a malformed analytics file must NOT crash the loader. However, the `json.load(f)` read (line 275) is unguarded: a corrupt/truncated analytics file (e.g. `{`) raises an opaque `json.JSONDecodeError`, violating that degrade-to-zero contract. Same class as TICKET-294/295/296.

## Evidence
- Line 275: `data = json.load(f)` in AnalyticsTracker.load — no try/except
- Line 278: existing non-dict guard proves the intended degrade value is `return 0`, not an exception.
- Verified by running the code: writing `{` to an analytics file makes `AnalyticsStore().load(path)` raise `json.JSONDecodeError`, while writing `[1,2,3]` (non-dict) correctly returns 0.

## Minimal additive fix
Wrap the `json.load(f)` read in `try/except json.JSONDecodeError: return 0`, matching the existing non-dict degrade path. Do NOT broaden the docstring — the contract is degrade-to-zero. Add 1-2 regression tests (corrupt `{` and truncated JSON both return 0).
