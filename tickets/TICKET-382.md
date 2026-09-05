# TICKET-382

- file: personal_index/content_dedup.py
- symptom: ContentDeduplicator.dedup_by_url() treats every item with an empty
  (missing) URL as a duplicate of every other empty-URL item, so N distinct
  items that simply lack a URL are collapsed to 1 and N-1 are "removed".
- evidence: dedup_by_url() builds url_groups keyed by normalize_url(url) with
  NO guard for the empty case (lines ~196-201: `normalized = normalize_url(url)`
  then `url_groups.setdefault(normalized, []).append(item)`). normalize_url("")
  returns "" (test_empty_url pins this), so all empty-URL items land in the
  same "" group and are flagged as duplicates. Probe:
  dedup_by_url([{'url':'','content':'a'},{'url':'','content':'b'},
  {'url':'','content':'c'}]) -> removed_count == 2, one group ('', ['','']).
  Contrast: dedup_by_hash() correctly guards with `if h:` (line ~167) so empty
  content is never treated as a duplicate. The two strategies are asymmetric:
  an item with no URL cannot be deduplicated BY URL, yet it is.
- minimal additive fix: in dedup_by_url(), skip items whose normalized URL is
  empty (mirror the `if h:` guard in _group_by_hash) so empty-URL items are
  neither grouped nor counted as removed. Additive: every non-empty-URL item
  is grouped/removed exactly as before; only the empty-URL case changes.
- class: (a) behavioral
- Issue: #601
