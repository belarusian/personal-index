# TICKET-273: migrations/base.py json.load missing non-dict guard

**Status:** RESOLVED
**Module:** personal_index/migrations/base.py
**Symptom:** `json.load` in `MigrationStore._load()` does not validate that the deserialized object is a dict. A corrupted store file containing `null`, a JSON list, or a bare number will cause an `AttributeError` when the loader calls `.get("migrations", [])` on the result.
**Evidence:** Line 213 `data = json.load(f)` followed by line 214 `data.get("migrations", [])` with no isinstance guard. Writer stores a dict `{"migrations": [...], "updated_at": "..."}`.
**Fix:** Added `if not isinstance(data, dict): return` after `json.load`.
**Tests:** 3 regression tests in tests/test_migrations/test_base.py (TestMigrationStoreLoadGuard).
**Issue:** #375
