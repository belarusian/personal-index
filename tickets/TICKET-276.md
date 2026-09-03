# TICKET-276: domains.py _load() missing non-dict JSON guard

- Status: RESOLVED
- File: personal_index/domains.py
- Symptom: `DomainManager._load()` calls `data.items()` after `json.load(f)`. If the file contains valid JSON that is not a dict (null, number, list, or string), `data.items()` raises AttributeError. The `except` clause only catches `(json.JSONDecodeError, KeyError)`, so a valid-JSON-but-wrong-type file crashes the constructor.
- Evidence: line 65 `data = json.load(f)` → line 66-68 `self._rules = {d: DomainRule.from_dict(r) for d, r in data.items()}` — no isinstance check; except at line 71 catches only JSONDecodeError/KeyError.
- Writer contract: `_save()` writes `json.dump({d: r.to_dict() for d, r in self._rules.items()}, f)` — a **dict**.
- Loader contract: `_load() -> None`; on error it degrades to `self._rules = {}` (empty rules, default-allow-all).
- Fix: After `json.load`, add `if not isinstance(data, dict): self._rules = {}; return` (matches the existing error-degrade contract: empty rules).
- Tests: null, number, list, valid-dict-still-works, valid-after-invalid-not-suppressed.
- Issue: #380
