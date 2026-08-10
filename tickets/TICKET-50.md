# TICKET-50: Unused modules — robots_parser.py, sitemap.py, content_filter.py, annotation.py, export.py, content_export_csv.py, export_markdown.py are never imported

## Title
Several modules are never imported by any other module in the codebase, indicating dead code

## Evidence
Grep for import patterns across the entire `personal_index/` directory shows these modules are never imported:

1. `personal_index/robots_parser.py` — defines `RobotsRule`, `RobotsPolicy`, `parse_robots_txt`, `is_allowed`. Duplicate of `personal_index/crawler/robots.py`. Never imported anywhere.
2. `personal_index/sitemap.py` — defines `SitemapEntry`. Duplicate of `personal_index/sitemap_builder.py`. Never imported anywhere.
3. `personal_index/content_filter.py` — defines `ContentFilter`. Duplicate of `personal_index/filter/engine.py`. Never imported anywhere.
4. `personal_index/annotation.py` — defines `AnnotationType`, `Annotation`, `AnnotationStore`. Duplicate of `personal_index/content_annotations.py`. Never imported anywhere.
5. `personal_index/export.py` — defines `ExportResult`. Duplicate of `personal_index/dashboard/export.py`. Never imported anywhere.
6. `personal_index/content_export_csv.py` — defines `ExportFormat` enum. Never imported anywhere.
7. `personal_index/export_markdown.py` — defines `ExportFormat` enum. Never imported anywhere.

Command used:
