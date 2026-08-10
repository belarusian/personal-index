# TICKET-80: Quoted type annotations that can be unquoted (UP037)

## Title
34 type annotations use unnecessary quotes — can be unquoted on Python 3.9+

## Evidence
ruff UP037 flags 34 locations across the codebase. These are self-referential type annotations in `__init__` methods that use quotes (e.g., `"ClassName"`) when `from __future__ import annotations` is already present, making quotes unnecessary.

Key locations:
1. `personal_index/api/models.py:38,42` — `"APIResponse[T]"`
2. `personal_index/auth/tokens.py:32` — quoted annotation
3. `personal_index/config/__init__.py:25,53,68` — quoted annotations
4. `personal_index/content_annotations.py:71` — quoted annotation
5. `personal_index/content_categorizer.py:207,210` — quoted annotations
6. `personal_index/content_collections.py:57` — quoted annotation
7. `personal_index/content_dedup.py:48` — quoted annotation
8. `personal_index/content_feed.py:54,231` — quoted annotations
9. `personal_index/content_priority.py` — 12 quoted annotations
10. `personal_index/crawler/__init__.py:45` — quoted annotation
11. `personal_index/domains.py:36` — quoted annotation
12. `personal_index/models.py` — 9 quoted annotations

## Impact
- Quotes are unnecessary when `from __future__ import annotations` is present (PEP 563)
- Unquoted annotations are more readable and consistent

## Suggestion
Run `ruff check --fix --select=UP037` to automatically remove unnecessary quotes from all 34 locations.
