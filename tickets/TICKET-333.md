# TICKET-333 — content_dedup.dedup_all docstring over-promises "all deduplication strategies"

- Status: OPEN
- Class: (b) doc/behavior drift
- Module: personal_index/content_dedup.py
- Issue: #504

## Symptom
The `ContentDeduplicator.dedup_all` docstring (line 325) claims it will
"Run all deduplication strategies and combine results." The class defines
THREE strategies (`dedup_by_hash`, `dedup_by_url`, `dedup_by_similarity`),
but `dedup_all` invokes only TWO of them: `dedup_by_url` (line 334) and
`dedup_by_hash` (line 346). It never calls `dedup_by_similarity`, so the
similarity strategy is silently omitted. "All deduplication strategies" is
an over-promise: the method actually runs the URL + content-hash strategies
only.

## Evidence
- `sed -n '321,333p' personal_index/content_dedup.py` shows the docstring
  "Run all deduplication strategies and combine results."
- `grep -n 'dedup_by_similarity\|dedup_by_hash\|dedup_by_url'
  personal_index/content_dedup.py` shows `dedup_by_similarity` is defined
  (line 230) but is NEVER called inside `dedup_all`; only `dedup_by_url`
  (line 334) and `dedup_by_hash` (line 346) are invoked.
- The class docstring (lines 135-139) is accurate — it says the class
  "Supports exact hash matching, URL normalization, and similarity-based
  deduplication," which is true because all three methods exist. The drift
  is confined to the `dedup_all` method docstring, which overstates what
  that single method runs.

## Minimal additive fix
Correct the `dedup_all` docstring to describe only the strategies actually
run. Change line 325 from
"Run all deduplication strategies and combine results." to
"Run the URL and content-hash deduplication strategies and combine
results." (the real behavior: URL + hash only; similarity is a separate
strategy the caller invokes directly via `dedup_by_similarity`).

Add ONE regression test
`TestContentDedupDocstring::test_dedup_all_docstring_does_not_promise_all_strategies`
that asserts the `dedup_all` docstring does not claim "all deduplication
strategies" (i.e. the word "all" is absent from the docstring), so the
over-promise cannot silently return.
