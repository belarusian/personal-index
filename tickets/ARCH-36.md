# ARCH-36: url_dedup — `get_duplicates` / `get_stats` can never report the duplicates actually detected (the dedup record is silently discarded)

Status: OPEN
Component: `personal_index/url_dedup.py`
Issue: #1101
Refs: ARCH-2 (#983 umbrella)

## Symptom

`URLDeduplicator.add_url` stores a URL **only when it is not a duplicate**
(the `if not result.is_duplicate:` guard). The add-time fuzzy check in
`check_duplicate` guarantees that, within a single domain, every stored URL is
pairwise `< _fuzzy_threshold` from every other stored URL: a URL that would
score `>= _fuzzy_threshold` against an already-stored URL is rejected and
never stored.

`get_duplicates` then re-scans **only the stored URLs** and reports pairs
scoring `>= _fuzzy_threshold`. By the invariant above, no two stored URLs in a
domain can ever score `>= _fuzzy_threshold`, so `get_duplicates` returns `{}`
for every input the deduplicator actually processed, and
`get_stats()["total_duplicate_groups"]` is always `0`.

The duplicates the module *does* detect (the `fuzzy_match` / `exact_match`
`DedupResult`s returned by `check_duplicate` / `add_url`) are **never
recorded** in the object's state — they exist only in the transient
`DedupResult` the caller must capture. The docstring promises "Get all
detected duplicates grouped by canonical URL," but the method can only ever
return an empty dict. This is the single most important hole in the module:
the introspection API is structurally dead, so a caller relying on
`get_duplicates` / `get_stats` to audit what was deduplicated gets a silent
false negative.

## Public contract (target)

`add_url` must **record** each detected duplicate (the normalized URL → the
matched original, with `reason` and `similarity_score`) in a separate
`_duplicates` structure, and `get_duplicates` must return that recorded map
(grouped by canonical / first-seen URL) rather than re-deriving it from the
non-duplicate-only `_seen_urls`. Concretely:

- `add_url` records a duplicate entry whenever `check_duplicate` returns
  `is_duplicate=True`, keyed by the matched canonical (first-seen) original.
- `get_duplicates()` returns `{canonical_original: [duplicate_original, ...]}`
  for every duplicate actually detected, in detection order.
- `get_stats()["total_duplicate_groups"]` returns the number of canonical
  groups in that recorded map (not a re-scan of `_seen_urls`).
- `clear()` also empties the recorded-duplicate structure.

## Acceptance criteria

1. After `add_url` on a URL that is an **exact** duplicate of a stored URL,
   `get_duplicates()` contains the duplicate grouped under the first-seen
   original.
2. After `add_url` on a URL that is a **fuzzy** duplicate (same domain, path
   ratio `>= threshold`), `get_duplicates()` contains it grouped under the
   matched original.
3. `get_stats()["total_duplicate_groups"]` equals the number of canonical
   groups reported by `get_duplicates()` (both `> 0` after duplicates are
   detected).
4. `get_duplicates()` still returns `{}` when no duplicates were detected.
5. `clear()` resets the recorded-duplicate structure so a subsequent
   `get_duplicates()` returns `{}`.

## Pinning tests to add (implementer)

- `test_get_duplicates_reports_exact_duplicate`: add `https://a.com/x` then
  `https://a.com/x/` (normalizes identically); assert `get_duplicates()`
  groups the second under the first (pins the exact-match record path).
- `test_get_duplicates_reports_fuzzy_duplicate`: add `https://a.com/article-1`
  then a same-domain URL whose path ratio is `>= threshold` (e.g.
  `https://a.com/article-11`); assert it is grouped under the first (pins the
  fuzzy-match record path — the guard/early-return case is the no-duplicate
  input below).
- `test_get_duplicates_empty_when_no_duplicates`: add two distinct same-domain
  URLs whose path ratio is `< threshold`; assert `get_duplicates() == {}`
  (pins the guard path).
- `test_get_stats_duplicate_groups_matches`: after detecting duplicates, assert
  `get_stats()["total_duplicate_groups"] == len(get_duplicates())` and `> 0`.
- `test_clear_resets_duplicates`: detect a duplicate, `clear()`, then assert
  `get_duplicates() == {}` and `get_stats()["total_duplicate_groups"] == 0`.

## Docs

`docs/url-dedup.md` (authored this cycle) documents the current behavior and
lists this as the primary contract hole. Update the `get_duplicates` /
`get_stats` entries and the "Contract Holes" section in the **same PR** that
implements the fix, so the page reflects the corrected record-and-report
semantics.
