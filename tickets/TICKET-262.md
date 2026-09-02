# TICKET-262: ContentVersioning._load crashes on non-dict JSON (AttributeError)

**Status**: OPEN
**Module**: personal_index/content_versioning.py
**Symptom**: If the storage file contains valid JSON that is not a dict (e.g., `null`, a list, a number), `ContentVersioning.__init__` crashes with `AttributeError: 'NoneType' object has no attribute 'items'` instead of gracefully resetting to empty state.
**Evidence**: Line 53 `data = json.load(f)` followed by line 56 `data.items()` — the except clause on line 66 catches `(json.JSONDecodeError, KeyError, TypeError)` but NOT `AttributeError`. Reproduced: writing `null` to the storage file and instantiating `ContentVersioning(storage_path=...)` raises `AttributeError`.
**Fix**: After `json.load`, check `isinstance(data, dict)`; if not, reset `self._versions = {}` and return.
**Issue**: #353
