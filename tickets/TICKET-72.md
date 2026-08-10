# TICKET-72: Unnecessary `elif`/`else` after `return` (RET505)

## Title
Multiple functions have `elif` or `else` branches after a `return` statement, making them unreachable dead code paths

## Evidence
ruff RET505 flags 17 locations:

1. `personal_index/bookmark_export.py:162` — unnecessary `elif` after `return`
2. `personal_index/content_archive/compressor.py:25` — unnecessary `elif` after `return`
3. `personal_index/content_archive/compressor.py:33` — unnecessary `elif` after `return`
4. `personal_index/content_export_csv.py:94` — unnecessary `elif` after `return`
5. `personal_index/content_health.py:258` — unnecessary `else` after `return`
6. `personal_index/content_health.py:291` — unnecessary `elif` after `return`
7. `personal_index/content_priority.py:46` — unnecessary `elif` after `return`
8. `personal_index/content_priority.py:288` — unnecessary `elif` after `return`
9. `personal_index/content_scoring.py:89` — unnecessary `elif` after `return`
10. `personal_index/content_scoring.py:165` — unnecessary `elif` after `return`
11. `personal_index/content_type.py:273` — unnecessary `elif` after `return`
12. `personal_index/export.py:82` — unnecessary `elif` after `return`
13. `personal_index/export_markdown.py:79` — unnecessary `elif` after `return`
14. `personal_index/export_markdown.py:94` — unnecessary `elif` after `return`
15. `personal_index/filter/matcher.py:30` — unnecessary `elif` after `return`
16. `personal_index/formatter.py:136` — unnecessary `elif` after `return`
17. `personal_index/formatter.py:146` — unnecessary `elif` after `return`
18. `personal_index/importer.py:70` — unnecessary `elif` after `return`
19. `personal_index/search_facets/facet_builder.py:110` — unnecessary `elif` after `return`

Example pattern:
