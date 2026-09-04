# TICKET-355: Sitemap.get_urls docstring says "all" but filters to valid http/https entries

- **File:** personal_index/sitemap.py
- **Function:** Sitemap.get_urls (line 49)
- **Symptom:** Docstring claims "Get all URLs from entries." but the body is
  `[e.loc for e in self.entries if e.is_valid()]` — it only returns loc values
  from entries whose loc starts with "http://" or "https://" (per is_valid).
  The blanket "all" omits the filtering condition.
- **Evidence:** Line 51: `return [e.loc for e in self.entries if e.is_valid()]`
  Line 28-29: `is_valid` checks `self.loc and self.loc.startswith(("http://", "https://"))`
- **Minimal additive fix:** Reword docstring to "Get URLs from entries that have
  a valid http/https location." Add one behavior test that pins the corrected
  claim: a Sitemap with one valid (https://) entry and one invalid (bare domain)
  entry returns only the valid URL from get_urls().
- **Status:** OPEN
Issue: #548
