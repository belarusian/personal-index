# TICKET-265: ScheduleStore._load crashes on non-dict JSON storage

**Status**: RESOLVED
**Module**: `personal_index/scheduler.py`
**Symptom**: `ScheduleStore._load` (line ~58) calls `data.items()` on the result of `json.load(f)` without verifying it is a dict. If the storage file contains valid JSON that is not a dict (null, list, number), an `AttributeError` is raised. The except clause catches `(json.JSONDecodeError, KeyError, TypeError)` but NOT `AttributeError`.

**Evidence**:
- `sed -n '58,59p' personal_index/scheduler.py`: `data = json.load(f)` followed by `for name, entry_data in data.items():`
- Live reproduction: writing `null`, `[1,2,3]`, `42` to storage file and instantiating `ScheduleStore(path=...)` raises `AttributeError: 'NoneType'/'list'/'int' object has no attribute 'items'`
- Same defect class as TICKET-262/263/264 (content_versioning.py, interests.py, index.py)

**Fix**: Add `if not isinstance(data, dict): self._entries = {}; return` immediately after `json.load(f)`. Add 3 regression tests (null/list/number storage resets to empty).

**Issue**: #359
