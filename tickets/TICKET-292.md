# TICKET-292: config/__init__.py AppConfig.load and ConfigManager.load unguarded json.load

- Status: RESOLVED
- Issue: #415
- Module: personal_index/config/__init__.py
- Function: AppConfig.load (line 68) and ConfigManager.load (line 85)

## Symptom
Both load methods already degrade to a default config on non-dict JSON (the `if not isinstance(data, dict): return cls()/AppConfig()` guard at lines 73-74 and 90-91), establishing the contract that a malformed config file must NOT crash the loader. However, the `json.load(f)` read (lines 72 and 89) is unguarded: a corrupt/truncated config file (e.g. `{`) raises an opaque `json.JSONDecodeError`, violating that degrade-to-defaults contract.

## Evidence
- Line 72: `data = json.load(f)` in AppConfig.load — no try/except
- Line 89: `data = json.load(f)` in ConfigManager.load — no try/except
- Lines 73-74 / 90-91: existing non-dict guard proves the intended degrade value is a default config (return cls() / AppConfig()), not an exception.
- Verified by running the code: writing `{` to a config file makes both `AppConfig.load(path)` and `ConfigManager(path).load()` raise `json.JSONDecodeError`, while writing `[1,2,3]` (non-dict) correctly returns a default AppConfig.
- Existing tests (tests/test_config.py TestAppConfigLoadNonDictGuard / TestConfigManagerLoadNonDictGuard) cover only non-dict JSON (null, list, number), not corrupt JSON.

## Minimal additive fix
Wrap each `json.load(f)` read in `try/except json.JSONDecodeError: return cls()` (AppConfig.load) / `return AppConfig()` (ConfigManager.load), matching the existing non-dict degrade path. Do NOT broaden the docstring — the contract is degrade-to-defaults, and the code must honor it for the corrupt-JSON case too. Add 2 regression tests (corrupt JSON `{` returns a default AppConfig for each method).
