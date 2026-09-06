# TICKET-464: TopicDetector.detect generic docstring (class-(b) doc-drift)

**File:** `personal_index/content_tagger/detector.py`
**Function:** `TopicDetector.detect` (line 121)
**Symptom:** One-line docstring `"""Detect topics in the given text."""` does not enumerate the actual behavior: empty/whitespace guard, per-topic keyword counting, confidence formula, and sort order.
**Evidence:** Line 122: `"""Detect topics in the given text."""`
**Body performs:**
1. Returns `[]` immediately if `text` is falsy or whitespace-only
2. Lowercases the text once; for each registered topic, sums `re.findall` counts over all of the topic's keywords (case-insensitive)
3. Emits a `Tag` for a topic only when its total `match_count > 0` (each topic at most once)
4. Confidence = `min(0.5 + match_count * 0.1, 1.0)`, rounded to 2 decimals
5. Returns tags sorted by confidence descending
**Fix:** Reword docstring to enumerate the guard, counting, confidence formula, and sort order. NO behavior change. Add pinning test.
**Issue:** #769
**Status:** OPEN
