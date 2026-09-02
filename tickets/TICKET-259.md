# TICKET-259: Interest.matches/score crash on non-string topics elements

**Status**: RESOLVED
**File**: `personal_index/models.py`
**Symptom**: If `Interest.topics` contains a non-string element (e.g., an int or None),
both `Interest.matches()` (line 102) and `Interest.score()` (line 132) raise
`AttributeError: 'int' object has no attribute 'lower'`, crashing the entire interest
matching pipeline (`matches_any`, `total_score`). The `keywords` loop immediately above
(lines 99, 129) is protected by `isinstance(kw, str)`, but `topics` is not.

**Evidence**:
- Line 99: `if isinstance(kw, str) and kw.lower() in text_lower:` (keywords - guarded)
- Line 102: `if topic.lower() in text_lower:` (topics - UNGUARDED)
- Line 129: `if isinstance(kw, str):` (keywords - guarded)
- Line 132: `total += text_lower.count(topic.lower())` (topics - UNGUARDED)

**Minimal additive fix**: Add `isinstance(topic, str)` guard in both the `matches`
and `score` topics loops, consistent with the existing `keywords` handling.

**Issue**: #347
