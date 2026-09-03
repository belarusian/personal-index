# TICKET-314: url_utils.urls_are_equivalent reports two different non-http/https URLs as equivalent

- Status: OPEN
- Module: personal_index/url_utils.py
- Symptom: `urls_are_equivalent(url1, url2)` (url_utils.py:189) returns
  `normalize_url(url1) == normalize_url(url2)`. `normalize_url` returns `None` for any URL
  whose scheme is not http/https (url_utils.py:82-83) and for empty input (url_utils.py:65).
  Therefore two *distinct* non-http/https URLs (e.g. `mailto:a@x.com` vs `mailto:b@y.com`, or
  `ftp://a.com/f` vs `ftp://b.com/g`) both normalize to `None` and compare equal, so the
  function reports them as "equivalent" — contradicting its docstring ("equivalent after
  normalization").
- Evidence: personal_index/url_utils.py lines 189-191 — `return normalize_url(url1) ==
  normalize_url(url2)` with no `None` guard.
  `python3 -c "from personal_index.url_utils import urls_are_equivalent as e; print(e('ftp://a/x','mailto:b@y'))"`
  -> `True` (two different URLs reported equivalent). Existing tests
  (tests/test_url_utils.py:290-307) only exercise http/https, so no test pins the buggy behavior.
- Minimal additive fix: in `urls_are_equivalent`, treat a `None` normalization as "not
  equivalent":
      n1 = normalize_url(url1)
      n2 = normalize_url(url2)
      if n1 is None or n2 is None:
          return False
      return n1 == n2
  Add regression tests for two distinct non-http/https URLs and for empty input.
- Issue: #462
