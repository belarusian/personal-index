# TICKET-2: Dead non-CLI modules — content_cache, content_diff, content_timeline, content_transform, health

## Evidence

The following modules are **never imported** by any source module or test file:

- `personal_index/content_cache.py` — separate from `personal_index/cache.py` (LRUCache) and `personal_index/content_cache.py` (ContentCache). Not imported anywhere.
- `personal_index/content_diff.py` — content diffing utility. Not imported anywhere.
- `personal_index/content_timeline.py` — timeline functionality. Not imported anywhere.
- `personal_index/content_transform.py` — content transformation. Not imported anywhere.
- `personal_index/health.py` — thin wrapper that imports `content_health`. Not imported anywhere.

Verified by scanning all `import` statements in `personal_index/*.py` and `tests/*.py`.

## Impact

- Dead code increases maintenance burden and confusion
- `health.py` is a thin wrapper around `content_health` that nobody uses
- `content_cache.py` may duplicate `cache.py` functionality

## Suggestion

Remove these 5 dead modules. If any contain useful logic, integrate it into the active modules that serve similar purposes.
