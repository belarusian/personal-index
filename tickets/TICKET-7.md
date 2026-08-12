# TICKET-7: Duplicate functionality across module pairs

## Evidence

Multiple module pairs provide overlapping functionality:

| Pair | Module A | Module B |
|------|----------|----------|
| Cache | `cache.py` (28 defs) | `content_cache.py` (26 defs) |
| Export | `export.py` (18 defs) | `content_exporter.py` (18 defs) |
| Versioning | `versioning.py` (17 defs) | `content_versioning.py` (16 defs) |
| Webhooks | `webhook.py` (16 defs) | `content_webhooks.py` (21 defs) |
| Notifications | `notifications.py` (40 defs) | `content_notifications.py` (21 defs) |
| Analytics | `analytics.py` (22 defs) | `content_analytics.py` (15 defs) |
| Search | `search_index.py` (14 defs) | `content_search.py` (36 defs) |
| Dedup | `url_dedup.py` (17 defs) | `content_dedup.py` (22 defs) |
| Filter | `url_filter.py` (18 defs) | `content_filter.py` (13 defs) |

Additionally, export has 5 separate modules:
- `export.py` (18 defs)
- `content_exporter.py` (18 defs)
- `export_markdown.py` (17 defs)
- `content_export_csv.py` (14 defs)
- `bookmark_export.py` (13 defs)

## Impact

- Developers don't know which module to use for a given task
- Bug fixes must be applied to multiple modules
- API surface is confusing and inconsistent
- Maintenance burden is doubled for each pair

## Suggestion

For each pair, determine which is the "canonical" implementation (likely the `content_*` variant based on `__init__.py` exports) and:
1. Deprecate the non-canonical module
2. Add a thin compatibility wrapper if needed
3. Update all imports to use the canonical module
4. Remove the deprecated module in the next major version

For the export modules, consolidate into a single `content_exporter.py` with format-specific methods.
