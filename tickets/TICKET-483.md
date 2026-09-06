# TICKET-483: _extract_url_hints false-positives on TLDs via `part in hint_word`

- **File:** personal_index/content_categorizer.py
- **Symptom:** `_extract_url_hints` matches a URL part against a hint word in
  BOTH directions: `if hint_word in part or part in hint_word` (line 571).
  The `part in hint_word` direction lets a short URL part (notably the TLD
  `com`) match a longer hint word that merely contains it:
  - `com` is a substring of `corp` (business) -> EVERY `*.com` URL gets a
    spurious `business` hint.
  - `com` is a substring of `eco` (environment) -> `*.com` URLs can also get
    a spurious `environment` hint.
  Observed: `_extract_url_hints("https://example.com/")` -> `{"business"}`;
  `_extract_url_hints("https://news.com/")` -> `{"business","politics"}`;
  `_extract_url_hints("https://healthcare.com/clinic")` -> `{"business","health"}`.
  The spurious `business` hint inflates the business topic score (URL_HINT_BOOST
  0.3 * weight) and can surface "business" as a topic for content that has no
  business signal at all.
- **Evidence:** line 571 `if hint_word in part or part in hint_word:`.
- **Minimal additive fix:** drop the `part in hint_word` direction so a hint
  word must appear WITHIN a URL part (the intended direction). The hint lists
  already contain the short forms ("tech", "dev", "eco", ...), so no intended
  match is lost. After the fix:
  - `https://example.com/` -> `set()`
  - `https://news.com/` -> `{"politics"}`
  - `https://healthcare.com/clinic` -> `{"health"}`
  - `https://dev-blog.com/api` -> `{"technology"}`
- **Test:** add `test_extract_url_hints_no_tld_false_positive` asserting
  `business` is NOT in the hints for a plain `*.com` URL, and that the intended
  topic is still detected for `dev-blog.com/api`. Fails pre-fix, passes post-fix.

Status: OPEN
Issue: #821
