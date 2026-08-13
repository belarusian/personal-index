# TICKET-12-1: Refactor `sitemap.SitemapParser.parse` (58L, line 61)

## What's wrong

`SitemapParser.parse` in `personal_index/sitemap.py` (line 61) is 58 lines and handles three distinct concerns:
1. XML parsing + error handling
2. Sitemap index detection and URL extraction (with dual namespace fallback)
3. Regular sitemap entry iteration

The sitemap index parsing logic is duplicated: once for namespaced elements (`ns:sitemap`) and once for non-namespaced (`sitemap`), with identical URL resolution logic inside each loop.

## Evidence
