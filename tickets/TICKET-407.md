# TICKET-407 — dedup_by_url docstring over-promise (class b)

- File: personal_index/content_dedup.py
- Function: ContentDeduplicator.dedup_by_url (line ~204)
- Symptom: docstring is a blanket "Deduplicate items by normalized URL." +
  generic Args/Returns. It does NOT enumerate:
  * grouping by `normalize_url(url)` (trailing slash / fragment removed,
    scheme+host lowercased);
  * the guard path: items whose normalized URL is empty are SKIPPED (not
    grouped) — mirrors the `if h:` guard in _group_by_hash;
  * only groups with >1 item become a DuplicateGroup (representative = first
    url, duplicates = remaining urls, similarity_score=1.0,
    dedup_method="normalized_url");
  * removed_count = sum(len(duplicates)) over groups;
  * returned DedupResult fields: total_items=len(items),
    unique_items=len(items)-removed, duplicate_groups, removed_count,
    method="url".
- Evidence: lines 204-247 (docstring 208-214 vs body 215-247).
- Minimal additive fix: reword docstring to the exact conditional + guard path;
  add ONE pinning test asserting the RETURNED DedupResult fields + the
  empty-URL guard path (an item with no URL stays unique, not grouped).
- Status: OPEN
- Issue: #652
