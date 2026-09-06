# TICKET-522: sitemap.SitemapParser.get_recent_entries docstring is a one-liner placeholder (class-(b) doc-drift)

- **File:** `personal_index/sitemap.py`
- **Symptom:** `SitemapParser.get_recent_entries` (line 185) carried only the
  one-liner placeholder `"""Get entries modified within the last N days."""`
  (line 188). The body performs a more specific contract the placeholder does
  not state: it iterates `sitemap.entries` in order, skips entries whose
  `lastmod` is falsy (None/empty), parses each remaining `lastmod` with
  `datetime.fromisoformat` after replacing a trailing `"Z"` with `"+00:00"`,
  skips entries whose `lastmod` raises `ValueError`/`TypeError`, and includes an
  entry when `(datetime.now(timezone.utc) - lastmod).days <= days` (inclusive
  boundary). The reader cannot tell which entries are skipped or that the
  boundary is inclusive.
- **Evidence line:** `personal_index/sitemap.py:188`
  (`"""Get entries modified within the last N days."""`)
- **Minimal additive fix:** reword the docstring to the exact contract the body
  performs (falsy-lastmod skip, `Z`->`+00:00` isoformat parse,
  `ValueError`/`TypeError` skip, inclusive `<= days` boundary, returns a new
  list). Add ONE pinning test class that calls `get_recent_entries` and asserts
  the returned list (main path: recent included, old excluded; guard paths:
  no-lastmod and unparseable-lastmod both skipped; plus an empty-sitemap case);
  do NOT assert on the docstring wording.
- **Status:** OPEN
- **Issue:** #910
