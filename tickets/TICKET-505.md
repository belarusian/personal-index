# TICKET-505: URLDeduplicator.normalize_url docstring under-specifies the contract

- **File:** personal_index/url_dedup.py
- **Function:** URLDeduplicator.normalize_url
- **Class:** (b) docstring drift (under-specification)
- **Symptom:** The docstring is a blanket one-liner ("Normalize a URL for
  comparison.") that omits the exact transformations the body actually performs.
- **Evidence:** personal_index/url_dedup.py line 34 (docstring) vs lines 35-43
  (body). The body performs SIX distinct transformations in order:
  1. drop the URL fragment (`parsed._replace(fragment="")`),
  2. strip a trailing slash from a non-root path,
  3. sort query parameters alphabetically (first value only),
  4. lowercase the scheme and netloc,
  5. remove a leading `www.` from the netloc,
  6. remove common tracking parameters (utm_*, fbclid, gclid).
  A reader cannot tell any of this from the current docstring.
- **Minimal additive fix:** reword the docstring to enumerate the exact
  transformations in the order the body performs them (never a blanket
  adjective), and add ONE behavior test that pins the corrected claim against
  the returned string for a complex URL (fragment + trailing slash + unsorted
  query + uppercase scheme/netloc + www + tracking param) alongside the
  guard-path input (a URL with no query/fragment that must be returned
  unchanged).
- **Status:** RESOLVED
- **Issue:** #864
