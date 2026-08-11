# TICKET-005: mypy error — `max()` key argument type mismatch in insights

**File:** `personal_index/content_analytics/insights.py:74,136`

**What's wrong:**
`max(tag_counts, key=tag_counts.get)` passes `dict.get` (an overloaded method) as the `key` argument to `max()`. Mypy cannot resolve the overloaded signature of `dict.get` as a valid `Callable[[str], ...]`.

**Evidence:**
