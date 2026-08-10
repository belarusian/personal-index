# TICKET-97: E402 — `from typing import ClassVar` placed before module docstring in 10 files

## Title
10 modules have `from typing import ClassVar` import before the module docstring, violating PEP 257

## Evidence
PEP 257 states: "The docstring for a module should generally be at the top of the module file, after any module-level comments and before any other code."

`from __future__ import annotations` is exempt (must be first), but `from typing import ClassVar` is a regular import and should come AFTER the docstring.

Affected files (all follow the same pattern — `__future__` on line 1, `ClassVar` on line 3, docstring on line 5):

1. `personal_index/bookmark_export.py` — line 3: `from typing import ClassVar`, line 5: docstring
2. `personal_index/content_categorizer.py` — line 3: `from typing import ClassVar`, line 5: docstring
3. `personal_index/content_enricher.py` — line 3: `from typing import ClassVar`, line 5: docstring
4. `personal_index/content_tagger/detector.py` — line 3: `from typing import ClassVar`, line 5: docstring
5. `personal_index/encoding.py` — line 3: `from typing import ClassVar`, line 5: docstring
6. `personal_index/export.py` — line 3: `from typing import ClassVar`, line 5: docstring
7. `personal_index/importer.py` — line 3: `from typing import ClassVar`, line 5: docstring
8. `personal_index/sitemap.py` — line 3: `from typing import ClassVar`, line 5: docstring
9. `personal_index/url_classifier.py` — line 3: `from typing import ClassVar`, line 5: docstring
10. `personal_index/validator.py` — line 3: `from typing import ClassVar`, line 5: docstring

All 10 files trigger ruff E402: "Module level import not at top of file" for the imports that follow the misplaced docstring.

## Impact
- ruff E402 violations (48 errors across these files)
- Module docstrings are not recognized as the first statement by tools that expect PEP 257 compliance
- `help(module)` may not display the docstring correctly in some environments

## Suggestion
Move `from typing import ClassVar` to AFTER the module docstring in all 10 files. The correct order should be:
1. `from __future__ import annotations` (must be first)
2. Module docstring
3. All other imports (including `from typing import ClassVar`)
