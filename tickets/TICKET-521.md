# TICKET-521: sitemap.SitemapParser.parse docstring is a one-liner placeholder (class-(b) doc-drift)

- **File:** `personal_index/sitemap.py`
- **Symptom:** `SitemapParser.parse` (line 59) carries only the one-liner
  placeholder `"""Parse sitemap XML content."""` (line 62). The body performs a
  multi-step contract the placeholder does not state: two early-return guards
  (empty content, XML parse error), namespace stripping of the root tag, and a
  dispatch between a `<sitemapindex>` root and a `<urlset>`/`<url>` root. The
  reader cannot tell what the guards return or which root tags are handled.
- **Evidence line:** `personal_index/sitemap.py:62`
  (`"""Parse sitemap XML content."""`)
- **Minimal additive fix:** reword the docstring to the exact contract the body
  performs:
  - empty/None `xml_content` -> return an empty `Sitemap(source_url=source_url)`.
  - `ET_fromstring` raising `ET_ParseError` -> return an empty
    `Sitemap(source_url=source_url)`.
  - strip a `{ns}` prefix from the root tag; if the root tag is `sitemapindex`,
    or the root contains a `ns:sitemapindex` child, delegate to
    `_parse_sitemap_index_items` and return the sitemap (populating
    `sitemap.sitemaps`).
  - otherwise iterate `ns:url` children, appending each non-None
    `_parse_url_element` result to `sitemap.entries`, and return the sitemap.
  Add ONE pinning test class that calls `parse` and asserts the returned
  `Sitemap` (main urlset branch AND the empty + parse-error guard paths); do NOT
  assert on the docstring wording.
- **Status:** OPEN
- **Issue:** #905
