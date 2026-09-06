# TICKET-500: normalize_url docstring omits its real contract

Status: RESOLVED
Module: personal_index/url_utils.py
Function: normalize_url (line 54)

## Symptom
The docstring reads `"""Normalize a URL by applying standard transformations."""` — a
generic description that omits the actual contract:

1. Returns `None` for empty input AND for any non-http/https scheme (e.g. `ftp://`, `javascript:`).
2. When `base_url` is given and the URL has no scheme, it is resolved against base_url first.
3. On a parse failure (ValueError/AttributeError) it returns the ORIGINAL url unchanged —
   NOT None (asymmetric with the empty/non-http rejection paths).
4. Each transformation is independently opt-out-able via flags: `remove_fragment`,
   `lowercase_path`, `remove_default_port`, `sort_query_params`.

## Evidence (verified live, 2026-09-06)
- `normalize_url("")` -> `None`
- `normalize_url("ftp://example.com")` -> `None`
- `normalize_url("http://[invalid")` -> `"http://[invalid"` (original returned, not None)
- `normalize_url("http://example.com/path?b=2&a=1", sort_query_params=False)` -> query unsorted
- `normalize_url("http://example.com/Path", lowercase_path=False)` -> path case preserved
- `normalize_url("http://example.com:80/path", remove_default_port=False)` -> `:80` kept

## Minimal additive fix
Reword the docstring to state the exact contract (None conditions, exception fallback,
flag semantics). Append pinning tests (TestNormalizeUrlContract) covering: exception
fallback returns original, opt-out flags, non-http scheme rejection, base_url resolution.

Issue: #856 (closed via PR #857)
