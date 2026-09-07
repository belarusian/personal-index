# Deduplication (`personal_index.content_dedup`)

Status: **spec** — audited against current code (cycle 169).

`ContentDeduplicator(similarity_threshold=0.9)` offers four strategies, each
returning a `DedupResult`.

## DedupResult
Fields: `total_items`, `unique_items`, `duplicate_groups` (list of
`DuplicateGroup`), `removed_count`, `method`, `is_duplicate`.
- `dedup_ratio` property: 0.0 when `total_items == 0`, else
  `removed_count / total_items`.
- `summary() -> str`: a 7-line human-readable block (total, unique, duplicates
  found, duplicate groups, dedup ratio, method).

## DuplicateGroup
Fields: `representative`, `duplicates` (list), `similarity_score`,
`dedup_method`. `total_count` property = `1 + len(duplicates)`.

## Strategies
- `dedup_by_hash(items, hash_field="content") -> DedupResult` — groups by
  `sha256(item.get(hash_field, ""))`; **empty hashes are skipped** (never
  grouped). A `DuplicateGroup` is built only for a hash group with >1 item:
  `representative` = first item's url, `duplicates` = remaining urls,
  `similarity_score=1.0`, `dedup_method="exact_hash"`. Returns
  `method="hash"`, `removed_count` = sum of `len(group)-1` over groups.
- `dedup_by_url(items) -> DedupResult` — groups by `normalize_url(item["url"])`
  (trailing slash + fragment removed, scheme/host lowercased); **empty
  normalized urls are skipped**. Groups with >1 item become a
  `DuplicateGroup` (`dedup_method="normalized_url"`, `similarity_score=1.0`).
  Returns `method="url"`.
- `dedup_by_similarity(items) -> DedupResult` — pairwise `text_similarity`
  (Jaccard over word sets); items with similarity >= threshold are grouped.
- `dedup_all(items) -> DedupResult` — runs url, then hash, then similarity
  (each stage reduces the list fed to the next), combining the three
  `duplicate_groups` lists and summing the three `removed_count` values;
  returns `method="combined"`.

## Contract holes
- None found this cycle. The `dedup_by_hash` / `dedup_by_url` docstrings were
  already reworded to exact-contract form in prior cycles (163-166).
