# TICKET-413: content_dedup.dedup_all over-promises "all deduplication strategies" (CLAIM TRUTH: implement the missing similarity stage)

Status: RESOLVED (cycle 53, PR #666, gh #665 closed, main 445156f)
File: personal_index/content_dedup.py
Function: ContentDeduplicator.dedup_all (line 374)
Issue: #665

## Symptom
The ORIGINAL claim for `dedup_all` (feat commit e3531c9) was:
    "Run all deduplication strategies and combine results."
The module defines THREE strategies: `dedup_by_hash`, `dedup_by_url`,
`dedup_by_similarity`. But `dedup_all` runs only URL + content-hash; it never
calls `dedup_by_similarity`. So the original claim is an over-promise the code
does not deliver.

## Evidence
- Original claim (git show e3531c9:personal_index/content_dedup.py:277):
  `"""Run all deduplication strategies and combine results."""`
- Current body (content_dedup.py:374-428) calls only `self.dedup_by_url(items)`
  and `self.dedup_by_hash(unique_items)`; `dedup_by_similarity` is never invoked.
- The parallel pipeline DOWNGRADED the docstring (TICKET-333, commit 9d87e43) to
  "Run the URL and content-hash deduplication strategies and combine results."
  and pinned `test_dedup_all_docstring_does_not_promise_all_strategies`
  (tests/test_content_dedup.py:474) asserting "all deduplication strategies" is
  NOT in the docstring.

## Classification
IMPLEMENTABLE. A caller reading the original claim reasonably expects all three
strategies to run; the code can deliver it in bounded scope by adding a third
similarity stage to the cascade (URL -> hash -> similarity), each stage reducing
the list for the next.

## Minimal additive fix
1. In `dedup_all`, after the content-hash stage, rebuild `unique_items` keeping
   the FIRST item per `content_hash(item.get("content", ""))` (empty content
   hashes to "" and the first such item survives, mirroring the URL stage), then
   run `sim_result = self.dedup_by_similarity(unique_items)`.
2. Combine `duplicate_groups` and `removed_count` across all three results.
3. Restore the ORIGINAL docstring claim "Run all deduplication strategies and
   combine results." with an accurate three-stage pipeline description.
4. Re-pin the pinning test to the ORIGINAL claim: rename
   `test_dedup_all_docstring_does_not_promise_all_strategies` to assert the
   docstring DOES promise all strategies; add a behavioral regression test
   proving a pair caught ONLY by similarity (distinct URLs, distinct content
   hashes, Jaccard >= threshold) is removed by `dedup_all`.
