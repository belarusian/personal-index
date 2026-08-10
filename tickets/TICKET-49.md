# TICKET-49: Duplicate class definitions across modules — dead code risk

## Title
Multiple classes are defined identically in different modules, creating confusion and dead code

## Evidence
The following classes/functions are duplicated across modules:

| Class/Function | Location 1 | Location 2 |
|---|---|---|
| `SearchResult` | `personal_index/models.py:272` | `personal_index/results.py:15` |
| `SearchIndex` | `personal_index/index.py:35` | `personal_index/search_index.py:16` |
| `Crawler` | `personal_index/crawler/__init__.py:50` | `personal_index/crawler/main.py:36` |
| `CrawlerConfig` | `personal_index/crawler/__init__.py:22` | `personal_index/crawler/main.py:24` |
| `ContentFilter` | `personal_index/content_filter.py:27` | `personal_index/filter/engine.py:24` |
| `RobotsPolicy` | `personal_index/robots_parser.py:19` | `personal_index/crawler/robots.py:21` |
| `RobotsRule` | `personal_index/robots_parser.py:11` | `personal_index/crawler/robots.py:12` |
| `parse_robots_txt` | `personal_index/robots_parser.py:77` | `personal_index/crawler/robots.py:72` |
| `is_allowed` | `personal_index/robots_parser.py:131` | `personal_index/crawler/robots.py:117` |
| `SitemapEntry` | `personal_index/sitemap.py:13` | `personal_index/sitemap_builder.py:16` |
| `Annotation` | `personal_index/content_annotations.py:22` | `personal_index/annotation.py:27` |
| `AnnotationType` | `personal_index/content_annotations.py:11` | `personal_index/annotation.py:14` |
| `ExportResult` | `personal_index/export.py:30` | `personal_index/dashboard/export.py:22` |
| `ExportFormat` | `personal_index/content_export_csv.py:15` | `personal_index/dashboard/export.py:14` | `personal_index/export_markdown.py:15` |
| `tokenize` | `personal_index/text_utils.py:305` | `personal_index/utils/__init__.py:66` | `personal_index/content.py:129` |

## Impact
- Developers may import from the wrong module, getting different behavior
- Code duplication means bug fixes must be applied in multiple places
- Increases maintenance burden and cognitive load
- Some duplicates may be dead code (never imported)

## Suggestion
1. Audit each duplicate pair to determine which is the "canonical" version
2. Remove dead duplicates or add deprecation warnings that re-export from the canonical module
3. For `Crawler`/`CrawlerConfig` in `crawler/__init__.py` vs `crawler/main.py` — the `__init__.py` likely re-exports from `main.py`; verify and document
4. Add a linting rule to prevent future duplicate class names across modules
