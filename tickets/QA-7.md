# QA-7: LRUCache(max_size=-1).put() raises KeyError: 'dictionary is empty'

Status: CLOSED (validator cycle 175: re-ran repro - LRUCache(max_size=-1).put() -> size 0, no crash; LRUCache(max_size=0).put() -> size 0; LRUCache(max_size=2) evicts correctly; deep test tests/deep/test_cache_adversarial.py 91 passed)
Issue: #1149

## Symptom

`LRUCache(max_size=-1)` followed by any `put()` call raises an unhandled
`KeyError: 'dictionary is empty'` from `OrderedDict.popitem(last=False)`.

The `put()` docstring promises: "while `len(self._cache) > self.max_size`
the least-recently-used entry (the front of the OrderedDict) is popped, so
the cache never exceeds `self.max_size` entries." With `max_size=-1`, the
condition `len > -1` is always true (even when `len == 0`), so the loop
pops past the empty dict and crashes.

## Exact Repro