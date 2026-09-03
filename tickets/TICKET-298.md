# TICKET-298: session.py SessionManager.load_session unguarded json.load

- Status: OPEN
- Issue: #425
- Module: personal_index/session.py
- Function: SessionManager.load_session (line 295)

## Symptom
SessionManager.load_session already degrades to None on non-dict JSON (the `if not isinstance(data, dict): return None` guard at line 296), establishing the contract that a malformed session file must NOT crash the loader. However, the `json.load(f)` read (line 295) is unguarded: a corrupt/truncated session file (e.g. `{`) raises an opaque `json.JSONDecodeError`, violating that degrade-to-None contract. Same class as TICKET-294/295/296.

## Evidence
- Line 295: `data = json.load(f)` in SessionManager.load_session — no try/except
- Line 296: existing non-dict guard proves the intended degrade value is `return None`, not an exception.
- Verified by running the code: writing `{` to a session file makes `load_session(path)` raise `json.JSONDecodeError`, while writing `[1,2,3]` (non-dict) correctly returns None.

## Minimal additive fix
Wrap the `json.load(f)` read in `try/except json.JSONDecodeError: return None`, matching the existing non-dict degrade path. Do NOT broaden the docstring — the contract is degrade-to-None. Add 1-2 regression tests (corrupt `{` and truncated JSON both return None).
