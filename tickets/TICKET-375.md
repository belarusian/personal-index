# TICKET-375 (RESOLVED)

- File: personal_index/url_utils.py
- Function: resolve_relative_url (line 289)
- Symptom: fragment-only (`#section`) and query-only (`?x=1`) relative
  references drop the base page path. `resolve_relative_url(
  "https://example.com/dir/page", "#section")` returns
  `https://example.com/dir#section` instead of
  `https://example.com/dir/page#section`.
- Evidence: probe vs stdlib reference:
    resolve_relative_url("https://example.com/dir/page", "#section")
      -> https://example.com/dir#section
    urllib.parse.urljoin("https://example.com/dir/page", "#section")
      -> https://example.com/dir/page#section
  Root cause: when parsed_rel.path is "" (fragment/query-only), the
  relative-path branch computes base_path.rsplit("/",1)[0] + "/" + "" which
  strips the last path segment (the page).
- Minimal additive fix: in the relative-path branch, when rel_path == ""
  keep the full base path (path = base_path) instead of the parent dir.
- Test: add fragment-only and query-only cases to TestResolveRelativeUrl
  (fails pre-fix, passes post-fix).
- Issue: #588
