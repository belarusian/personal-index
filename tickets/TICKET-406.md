# TICKET-406

- Status: RESOLVED (PR #651 merged, issue #650 closed)
- Issue: #650
- Module: personal_index/content_dedup.py
- Function: ContentDeduplicator.dedup_by_similarity
- Class: (b) doc-drift — blanket docstring

## Symptom
`dedup_by_similarity` docstring is a single blanket line:
"Deduplicate items by content similarity."
It does not enumerate the guard paths, the grouping rule, the return
fields, or the accepted-but-unused behavior of `compare_field`.

## Evidence
personal_index/content_dedup.py:257
    """Deduplicate items by content similarity."""

## Minimal additive fix
Reword the docstring to state the EXACT behavior:
- iterates items in order; for each unvisited seed i it calls
  _find_similarity_group, which compares item i's `compare_field` text
  against every LATER item j and groups those whose text_similarity is
  >= self.similarity_threshold (earlier items are never re-scanned).
- only groups with >1 item become a DuplicateGroup
  (representative = first url, duplicates = remaining urls,
  similarity_score = self.similarity_threshold, dedup_method="similarity");
  removed_count += len(group) - 1.
- empty/missing `compare_field` text yields text_similarity 0.0, so such
  items never group (guard path: they stay unique).
- returns DedupResult(total_items=len(items), unique_items=len(items)-removed,
  duplicate_groups=groups, removed_count=removed, method="similarity").
Add ONE pinning test that calls dedup_by_similarity directly (a duplicate
pair + one empty-content item) and asserts the RETURNED DedupResult fields
and the DuplicateGroup fields, pinning both the grouping rule and the
empty-content guard path.

## Line-shift guard
tests/test_content_dedup.py has no line-number references
(no lineno / _get_source_lines / _method_line_span / getsource, grep rc=1),
so adding docstring lines is safe.
