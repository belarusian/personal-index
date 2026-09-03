# TICKET-275: url_history.py load() missing non-list JSON guard

- Status: RESOLVED
- File: personal_index/url_history.py
- Symptom: `URLHistory.load()` iterates `data` directly after `json.load(f)`. If the file contains valid JSON that is not a list (null, number, dict, or list-of-non-dicts), the comprehension `[URLVisit.from_dict(d) for d in data]` raises TypeError/AttributeError.
- Evidence: line 159 `data = json.load(f)` → line 160 `self._history = [URLVisit.from_dict(d) for d in data]` — no isinstance check.
- Writer contract: `save()` writes `json.dump([v.to_dict() for v in self._history], f)` — a **list**.
- Loader contract: `load() -> int` ("Returns count loaded"); missing file → `return 0`.
- Fix: After `json.load`, add `if not isinstance(data, list): return 0` (matches the "nothing loaded" / count-zero contract).
- Tests: null, list-of-non-dicts, number, dict at the load site; valid-sibling-not-suppressed.
- Issue: #378
