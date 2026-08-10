# TICKET-2: Duplicate url_utils modules with divergent implementations

## Title
`personal_index/url_utils.py` and `personal_index/utils/url_utils.py` are near-duplicates with divergent implementations

## Evidence
Two files provide overlapping URL utility functions:

- `personal_index/url_utils.py` (225 lines) — has `extract_subdomain`, `get_tld`, `is_internal_link`, `remove_query_params`, `url_to_path`, `join_urls`, `extract_all_urls`, `is_robotstxt`, `is_sitemap`
- `personal_index/utils/url_utils.py` (136 lines) — has `resolve_relative_url`, `is_excluded_url`, `get_url_depth`, `is_same_domain`

Shared functions with different signatures:
- `normalize_url(url)` vs `normalize_url(url, base_url="")` — the utils version supports relative URL resolution and returns `Optional[str]`
- `extract_domain(url)` returns `str` vs `Optional[str]` — the utils version strips port numbers
- `is_excluded_url(url)` — identical logic in both files
- `is_same_domain(url1, url2)` — exists in both, but utils version uses `extract_domain` from its own module

Both share identical `EXCLUDED_EXTENSIONS` and `EXCLUDED_SCHEMES` constants.

## Impact
- Code duplication increases maintenance burden
- Different callers may get different behavior for the same operation (e.g., `normalize_url`)
- `extract_domain` in root module doesn't strip ports; utils version does
- Risk of silent bugs if one is updated but not the other

## Suggestion
1. Consolidate into a single `personal_index/url_utils.py` (the root-level one, as it's more widely imported)
2. Merge unique functions from `personal_index/utils/url_utils.py` into the root module
3. Update `personal_index/utils/url_utils.py` to re-export from the root module, or remove it entirely
4. Standardize return types (prefer `Optional[str]` over empty-string sentinel)
