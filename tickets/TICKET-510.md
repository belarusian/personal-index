# TICKET-510: url_dedup.py seen_count placeholder docstring under-describes behavior

- **File:** personal_index/url_dedup.py
- **Method:** `URLDeduplicator.seen_count` (line 29)
- **Defect class:** (b) docstring drift (under-specification)
- **Symptom:** The `seen_count` `@property` docstring is a bare name-echo placeholder ("Seen_count.") that states no behavior the body performs.
- **Evidence:**
  - L29-31 `seen_count`: a `@property` whose body is `return len(self._seen_urls)` — the number of distinct normalized URLs currently held in the deduplicator's `_seen_urls` map (normalized -> original). Returns an `int`.
- **Minimal additive fix:** Reword the placeholder to state the exact behavior the body performs (a `@property` returning `len(self._seen_urls)`, the count of distinct normalized URLs seen so far). Add ONE pinning behavior test that asserts the returned value equals the number of distinct normalized URLs added (normal case) AND that a normalized-duplicate add does not change the count (guard path: the same normalized URL is not double-counted), so the doc-only fix is witnessed.
- **Issue:** #876
- **Status:** OPEN
