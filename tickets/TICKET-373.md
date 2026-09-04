# TICKET-373: resolve_relative_url() corrupts query string in relative URLs

- File: personal_index/url_utils.py
- Function: resolve_relative_url() (line ~291)
- Symptom: When a relative URL carries a query string, the query is embedded
  into the path AND appended again by urlunparse, producing a doubled query.
- Evidence:
  - resolve_relative_url("https://example.com/base", "/page?x=1")
    -> 'https://example.com/page?x=1?x=1'  (expected 'https://example.com/page?x=1')
  - resolve_relative_url("https://example.com/base/", "page?x=1")
    -> 'https://example.com/base/page?x=1?x=1'
  - Cause: the "Relative path" branch assigns `path = relative_url` (or
    base_path + relative_url), which includes the query/fragment. urlunparse
    then appends parsed_rel.query a second time.
- Minimal additive fix: use `parsed_rel.path` (query/fragment are already
  supplied separately to urlunparse) when building the relative path, instead
  of the raw `relative_url` string.
- Test: add a test asserting the query is preserved exactly once for both
  root-relative and base-relative relative URLs (fails pre-fix, passes post-fix).

Issue: #584

## RESOLVED
Merged to main 61a37e2 (PR #585, squash); gh #584 closed; local gate green (5454 passed, ruff clean, mypy success); CI green (run 33918337336).
