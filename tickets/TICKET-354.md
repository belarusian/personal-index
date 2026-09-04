# TICKET-354: content_aggregator.ContentAggregator.merge_all docstring omits deduplicate branch + default

**File**: personal_index/content_aggregator.py
**Symptom**: `merge_all` docstring is the blanket claim "Merge all sources into a single list." which omits the named strategy branch the body performs: the `deduplicate: bool = True` argument. When True (the default), the body removes duplicate items keyed on `str(item.get("id") or item.get("title"))`, keeping the first occurrence. The docstring names neither the argument, its default, nor the dedup key/keep-first behavior.
**Evidence**:
- Line 26: `def merge_all(self, deduplicate: bool = True) -> list[dict[str, Any]]:`
- Line 27: `"""Merge all sources into a single list."""`
- Lines 33-40: `if deduplicate:` ... `key = str(item.get("id") or item.get("title"))` ... keep first via `seen` set.
**Minimal additive fix**:
1. Reword the docstring to state the exact dedup key (id, falling back to title), the keep-first behavior, and the deduplicate default (True).
2. Add ONE behavior test pinning the corrected claim against the returned list: two items sharing an id (different titles) collapse to the FIRST occurrence under the default call.
**Status**: RESOLVED
**Issue**: #546
