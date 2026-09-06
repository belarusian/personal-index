# TICKET-476: ViewResult dict-style access unscoped vs to_dict (class-(a) guard inconsistency)

- File: personal_index/content_timeline/timeline_view.py
- Method: ViewResult.__getitem__ / ViewResult.__contains__
- Symptom (class-a guard inconsistency): the dict-style access contract is
  unscoped. `__getitem__` uses `getattr(self, key)` and `__contains__` uses
  `hasattr(self, key)`, so EVERY attribute is addressable - including dunders
  such as `__class__` and `__dict__` (`'__class__' in result` is True,
  `result['__class__']` returns the type). This is inconsistent with
  `to_dict()`, which returns EXACTLY the five serialized fields
  (events, date, mode, total, summary). A dict-style container should expose
  the same key set as its `to_dict()` serialization, not the whole object
  attribute namespace.
- Evidence line: `def __getitem__` (line ~32, `return getattr(self, key)`) and
  `def __contains__` (line ~36, `return hasattr(self, key)`) vs
  `def to_dict` (line ~42, returns exactly events/date/mode/total/summary).
- Minimal additive fix: scope both `__getitem__` and `__contains__` to the
  five serialized fields (the same key set as `to_dict()`). `__getitem__`
  raises `KeyError` for any key outside that set; `__contains__` returns True
  only for those five keys (and still False for non-str keys). Add ONE pinning
  test class asserting the exact key set: the five fields are present, dunders
  are NOT present, out-of-set `__getitem__` raises KeyError, and the access
  contract matches `to_dict()` keys.
- Status: OPEN
- Issue: #800
