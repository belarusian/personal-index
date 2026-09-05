# TICKET-405

- Status: OPEN
- Class: (b) doc-drift
- File: personal_index/content_dedup.py
- Function: ContentDeduplicator.dedup_by_hash (line 145)

## Symptom
The docstring is the blanket adjective "Deduplicate items by content hash."
It does not enumerate the sub-components the body actually performs:
- the `hash_field` parameter (default "content") and that it is read via
  `item.get(hash_field, "")`;
- the guard that items whose `content_hash` is empty (empty content) are
  skipped and never grouped (mirrors the `if h:` guard in `_group_by_hash`);
- that a DuplicateGroup is built only for hash groups with >1 item, with
  representative = first item's url, duplicates = remaining urls,
  similarity_score=1.0, dedup_method="exact_hash";
- the returned DedupResult fields: total_items=len(items),
  unique_items=len(items)-removed, duplicate_groups, removed_count,
  method="hash".

## Evidence
personal_index/content_dedup.py:145-160 (docstring + body).

## Minimal additive fix
Reword the docstring to state the exact behavior (enumerate the guard path,
the group-building rule, and the returned DedupResult fields). Add ONE
pinning test that calls `dedup_by_hash` directly with a fresh result and
asserts the RETURNED DedupResult fields (total_items / unique_items /
removed_count / method) and the DuplicateGroup fields (representative /
duplicates / similarity_score / dedup_method), including the empty-content
guard path.

## Issue
Issue: #648
