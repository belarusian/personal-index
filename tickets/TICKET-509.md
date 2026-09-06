# TICKET-509: sitemap_builder.py placeholder docstrings under-describe behavior

- **File:** personal_index/sitemap_builder.py
- **Methods:** `SitemapEntry.to_element` (line 32), `SitemapBuilder.clear` (line 100), `SitemapBuilder.url_count` (line 105)
- **Defect class:** (b) docstring drift (under-specification)
- **Symptom:** Three docstrings are bare name-echo placeholders ("To_element.", "Clear.", "Url_count.") that state no behavior the body performs.
- **Evidence:**
  - L32 `to_element`: body builds a `<url>` Element and attaches exactly four SubElements — `loc` (text = self.url), `lastmod` (text = self.last_modified.strftime("%Y-%m-%dT%H:%M:%SZ")), `changefreq` (text = self.change_frequency), `priority` (text = f"{self.priority:.1f}"). Returns the `<url>` Element.
  - L100 `clear`: body calls `self.entries.clear()` — empties the builder's entries list in place. Returns None.
  - L105 `url_count`: body is a `@property` returning `len(self.entries)` — the number of entries currently held by the builder.
- **Minimal additive fix:** Reword each placeholder to state the exact behavior the body performs (enumerate the four to_element SubElements and their text formats; clear empties self.entries in place; url_count is len of self.entries). Add ONE pinning behavior test that asserts the to_element() returned `<url>` Element has EXACTLY the four documented SubElements (loc/lastmod/changefreq/priority) with the documented text formats, and asserts the ABSENCE of any sibling SubElement (e.g. no `<url>` child / no extra tag), so the doc-only fix is witnessed.
- **Issue:** #872
- **Status:** RESOLVED (merged via PR #875, CI run 34037055201, gh #872 closed)
