# TICKET-9: Dead modules — not imported by any production or test code

## Title
8 modules are defined but never imported anywhere in the codebase

## Evidence
Static analysis of all `import` statements across `personal_index/` and `tests/` reveals these modules are never imported:

| Module | File | Notes |
|--------|------|-------|
| `personal_index.api.routes` | `personal_index/api/routes.py` | API routes defined but never wired into server |
| `personal_index.content_favicon` | `personal_index/content_favicon.py` | Favicon extraction, no consumers |
| `personal_index.content_import_html` | `personal_index/content_import_html.py` | HTML bookmark import, no consumers |
| `personal_index.content_social_preview` | `personal_index/content_social_preview.py` | Social preview generation, no consumers |
| `personal_index.content_thumbnail` | `personal_index/content_thumbnail.py` | Thumbnail generation, no consumers |
| `personal_index.crawl_stats` | `personal_index/crawl_stats.py` | Crawl statistics, no consumers |
| `personal_index.migrations.001_initial_schema` | `personal_index/migrations/001_initial_schema.py` | Migration file, may be loaded dynamically |
| `personal_index.migrations.002_add_indexes` | `personal_index/migrations/002_add_indexes.py` | Migration file, may be loaded dynamically |

The migration files may be loaded dynamically by the migration runner, so they should be verified separately.

## Impact
- Dead code increases maintenance burden
- `api/routes.py` may indicate incomplete API server setup
- Content enrichment modules (favicon, social preview, thumbnail) are untested and unused
- Wasted CI/CD time compiling and type-checking unused code

## Suggestion
1. For `api/routes.py`: Verify if routes are loaded dynamically by FastAPI. If not, wire them into `api/server.py`.
2. For content enrichment modules: Either integrate them into the content pipeline or remove them.
3. For `crawl_stats.py`: Integrate into the crawler or remove.
4. For migration files: Verify the migration runner loads them dynamically. If so, mark as expected.
5. Add a linting rule to detect unused modules (e.g., `ruff` with `F401` at module level).
