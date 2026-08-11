# TICKET-004: mypy error — returning Any from function declared to return `T | None`

**File:** `personal_index/content_cache/cache_store.py:60`

**What's wrong:**
The `get` method returns `entry.value` which is typed as `Any`, but the method signature declares return type `T | None`. Mypy flags this as `[no-any-return]`.

**Evidence:**
