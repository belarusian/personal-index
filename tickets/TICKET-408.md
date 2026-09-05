# TICKET-408 — dedup_all docstring over-promise (class b)

- File: personal_index/content_dedup.py
- Function: ContentDeduplicator.dedup_all (line ~374)
- Symptom: docstring is a blanket "Run the URL and content-hash deduplication
  strategies and combine results." + generic Args/Returns. It does NOT
  enumerate the two-stage pipeline:
  * stage 1: run `dedup_by_url(items)` on the FULL input list;
  * stage 2: rebuild `unique_items` by keeping the FIRST item per
    `normalize_url(url)` (empty-URL items all normalize to the same empty key,
    so only the FIRST empty-URL item survives this stage);
  * stage 3: run `dedup_by_hash(unique_items)` on that reduced list (NOT on
    url_result.unique_items);
  * combine: `duplicate_groups = url_result.duplicate_groups +
    hash_result.duplicate_groups`, `removed_count = url_result.removed_count +
    hash_result.removed_count`;
  * returned DedupResult fields: total_items=len(items),
    unique_items=len(items)-total_removed, duplicate_groups, removed_count,
    method="combined".
  Note the asymmetry: `unique_items` is computed from the URL-normalized
  first-seen list, NOT from `url_result.unique_items`.
- Evidence: lines 374-411 (docstring 378-384 vs body 385-411).
- Minimal additive fix: reword docstring to the exact two-stage pipeline +
  combine rule + returned fields; add ONE pinning test asserting the RETURNED
  DedupResult fields (total_items / unique_items / removed_count /
  method="combined" / duplicate_groups) for an input that exercises both the
  URL-duplicate path and the content-hash-duplicate path.
- Status: RESOLVED (cycle 166, PR #655, merge on main)
- Issue: #654
