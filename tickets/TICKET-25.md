# TICKET-25: Duplicate `url_utils.py` — root-level and `utils/` submodule

## Title
Two `url_utils.py` modules with overlapping but different implementations

## Evidence
Two distinct URL utility modules:

1. **`personal_index/url_utils.py`** (352 lines) — Full implementation with `is_valid_url`, `normalize_url(url, remove_fragment, lowercase_path, remove_default_port, sort_query_params)`, `resolve_relative_url`, `extract_domain`, `is_excluded_url`, `get_url_depth`, `is_same_domain`, `EXCLUDED_EXTENSIONS`, `EXCLUDED_SCHEMES`

2. **`personal_index/utils/url_utils.py`** — Simpler implementation with `is_valid_url`, `normalize_url(url, base_url)` (different signature!), `resolve_relative_url`, `extract_domain`, `is_excluded_url`, `get_url_depth`, `is_same_domain`, `EXCLUDED_EXTENSIONS`, `EXCLUDED_SCHEMES`

Import usage:
- `personal_index/url_utils.py`: imported by `crawler/main.py:14`, `stats.py:11`, `content_filter.py:98`
- `personal_index/utils/url_utils.py`: imported by `utils/__init__.py:3`, `crawler/__init__.py:125`, `content.py:104`

The `normalize_url` function has **different signatures** between the two modules:
- Root: `normalize_url(url, remove_fragment=True, lowercase_path=True, remove_default_port=True, sort_query_params=True)`
- Utils: `normalize_url(url, base_url="")` — also resolves relative URLs

## Impact
- Different callers get different normalization behavior
- `normalize_url` in `utils/` resolves relative URLs; root version does not
- Maintenance burden: fixes must be applied to both

## Suggestion
1. Keep `personal_index/url_utils.py` as the canonical module (it's more feature-complete)
2. Remove `personal_index/utils/url_utils.py`
3. Update `utils/__init__.py` to re-export from the root module
4. Update all import sites to use `personal_index.url_utils`
