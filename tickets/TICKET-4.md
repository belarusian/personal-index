# TICKET-4: Missing test coverage for specific modules

## Title
Several standalone modules have no test files

## Evidence
After scanning all test files recursively (113 test files found), the following source modules have no corresponding tests:

| Module | Notes |
|--------|-------|
| `personal_index/content_favicon.py` | No `test_content_favicon.py` |
| `personal_index/content_import_html.py` | No `test_content_import_html.py` |
| `personal_index/content_social_preview.py` | No `test_content_social_preview.py` |
| `personal_index/content_thumbnail.py` | No `test_content_thumbnail.py` |
| `personal_index/crawl_stats.py` | No `test_crawl_stats.py` |
| `personal_index/dashboard/aggregator.py` | `test_dashboard/` only has `test_views.py` |
| `personal_index/dashboard/export.py` | No test |
| `personal_index/dashboard/stats.py` | No test |
| `personal_index/api/routes.py` | `test_api/` has no `test_routes.py` |
| `personal_index/api/models.py` | `test_api/` has no `test_models.py` (root `test_models.py` covers `personal_index/models.py`) |
| `personal_index/api/pagination.py` | `test_api/` has no `test_pagination.py` (root `test_pagination.py` covers `personal_index/pagination.py`) |
| `personal_index/config/models.py` | `test_config/` has no `test_models.py` |
| `personal_index/filter/engine.py` | `test_filter/` only has `test_matcher.py` |
| `personal_index/migrations/` | `test_migrations/` exists but may be sparse |

Additionally, 5 test files import from non-existent modules (see TICKET-1):
- `test_content_changelog.py`
- `test_content_diff.py`
- `test_content_pin.py`
- `test_content_rollback.py`
- `test_content_versioning.py`

## Impact
- Content enrichment features (favicons, social previews, thumbnails) untested
- Dashboard aggregation and stats untested
- API routes untested
- Filter engine untested
- 5 tests will fail on import with `ModuleNotFoundError`

## Suggestion
1. Add tests for `content_favicon`, `content_import_html`, `content_social_preview`, `content_thumbnail`, `crawl_stats`
2. Add `test_aggregator.py`, `test_export.py`, `test_stats.py` to `tests/test_dashboard/`
3. Add `test_routes.py` to `tests/test_api/`
4. Add `test_engine.py` to `tests/test_filter/`
5. Address TICKET-1 (non-existent modules) — either implement or remove
