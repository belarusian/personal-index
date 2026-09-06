# TICKET-480 — is_sitemap over-matches non-sitemap pages via bare substring

- **File:** personal_index/url_utils.py
- **Function:** is_sitemap
- **Symptom:** `is_sitemap` classifies a URL as a sitemap whenever the path
  contains the substring "sitemap" (`"sitemap" in path`). This over-matches
  unrelated pages whose names merely contain the word, e.g.
  `/about-sitemap`, `/sitemap-backup`, `/mysitemap-page` all return True.
- **Evidence (line ~383):** `return "sitemap" in path`
  Verified: is_sitemap('https://example.com/about-sitemap') == True (should be False).
- **Minimal additive fix:** treat a sitemap as a path component that STARTS
  with "sitemap" and carries a file extension (e.g. sitemap.xml,
  sitemap_index.xml, sitemap-news.xml). Keep true positives, drop the
  substring over-match.
- **Test:** add a pinning test asserting `/sitemap.xml` is True while
  `/about-sitemap`, `/sitemap-backup`, `/mysitemap-page` are False.
- Status: RESOLVED (merged via PR #813)
- Issue: #811
