# TICKET-5: Unused imports across multiple modules

## Title
Multiple modules have genuinely unused imports that should be cleaned up

## Evidence
Static analysis of all modules in `personal_index/` reveals unused imports. These are NOT `from __future__ import annotations` (which is a directive, not a name reference) and NOT type annotation references (which are strings under PEP 563).

### Confirmed unused imports (module name only appears in import line):

| File | Unused Imports |
|------|---------------|
| `personal_index/backup.py` | `gzip`, `shutil`, `tempfile`, `Set` |
| `personal_index/rss.py` | `datetime`, `timezone`, `urljoin` |
| `personal_index/health.py` | `hashlib`, `json`, `time`, `Storage` |
| `personal_index/validator.py` | `re` |
| `personal_index/content_type.py` | `Any`, `re` |
| `personal_index/content_search_fulltext.py` | `datetime`, `timezone` |
| `personal_index/importer.py` | `Dict`, `os` |
| `personal_index/text_utils.py` | `Any` |
| `personal_index/models.py` | `Optional` |
| `personal_index/similarity.py` | `Counter`, `Optional` |
| `personal_index/webhook.py` | `Optional`, `URLError` |
| `personal_index/url_history.py` | `field`, `time` |
| `personal_index/link_preview.py` | `Optional`, `field` |
| `personal_index/url_filter.py` | `field` |
| `personal_index/robots_parser.py` | `Optional`, `fnmatch` |
| `personal_index/content_health.py` | `time` |
| `personal_index/sitemap.py` | `Dict`, `StringIO`, `re` |
| `personal_index/content_enricher.py` | `Optional`, `STOPWORDS`, `word_frequency` |
| `personal_index/content_import_html.py` | `Optional` |
| `personal_index/rate_limiter.py` | `field` |
| `personal_index/cache.py` | `Generic` |
| `personal_index/robots_cache.py` | `urlparse` |
| `personal_index/export.py` | `Bookmark`, `Dict`, `os` |
| `personal_index/content_scoring.py` | `field`, `re` |
| `personal_index/url_classifier.py` | `Optional` |
| `personal_index/content_social_preview.py` | `uuid` |
| `personal_index/cli.py` | `Optional`, `os` |
| `personal_index/dedup.py` | `List`, `Set`, `field` |
| `personal_index/pipeline.py` | `Any` |
| `personal_index/content_scheduler.py` | `Path`, `Set`, `hashlib` |
| `personal_index/content_favicon.py` | `re`, `uuid` |
| `personal_index/serializer.py` | `asdict` |
| `personal_index/summarizer.py` | `Optional` |
| `personal_index/notifications.py` | `Optional` |
| `personal_index/analytics.py` | `defaultdict` |
| `personal_index/export_markdown.py` | `field`, `re` |
| `personal_index/progress.py` | `math` |
| `personal_index/pagination.py` | `field` |
| `personal_index/fuzzy_search.py` | `Optional`, `re` |
| `personal_index/url_dedup.py` | `Set`, `field`, `re` |
| `personal_index/tfidf.py` | `Optional` |
| `personal_index/link_analyzer.py` | `Optional`, `defaultdict` |
| `personal_index/health_report.py` | `platform` |
| `personal_index/throttle.py` | `defaultdict` |
| `personal_index/auth/sessions.py` | `datetime`, `secrets`, `timezone` |
| `personal_index/auth/api_keys.py` | `time` |
| `personal_index/migrations/base.py` | `time` |
| `personal_index/config/models.py` | `Optional` |
| `personal_index/config/loader.py` | `List`, `Optional` |

### `__init__.py` files with unused re-exports:
- `personal_index/auth/__init__.py` — imports 13 names that may not all be used externally
- `personal_index/search_facets/__init__.py` — imports 6 names
- `personal_index/content_tagger/__init__.py` — imports 3 names
- `personal_index/migrations/runner.py` — imports `BaseMigration`

## Impact
- Cluttered imports make code harder to read
- May indicate dead code or incomplete refactoring
- Some unused imports (like `os`, `shutil`, `tempfile`) could be security concerns if they suggest abandoned functionality

## Suggestion
1. Remove confirmed unused imports from each module
2. For `__init__.py` files, verify that re-exported names are actually used by external code
3. Add a linting rule (e.g., `flake8` with `F401` or `ruff` with `F401`) to prevent future unused imports
