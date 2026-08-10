# TICKET-18: Comprehensive audit - missing imports, dead code, unused variables

## Title
Multiple syntax and import issues fixed during audit

## Evidence

### Missing Imports (F821)
1. **personal_index/content_priority.py**:
   - `datetime`, `timezone`, `List`, `Dict` used but not imported
   - Fixed by adding: `from datetime import datetime, timezone` and `from typing import Dict, List`

2. **personal_index/content_timeline/timeline_view.py**:
   - `date` used in type hint but not imported
   - Fixed by adding: `from datetime import date`

### Unused Imports (F401)
Fixed in multiple modules:
- personal_index/crawler/__init__.py: Interest, InterestType, is_same_domain
- personal_index/crawler/main.py: Interest, InterestType
- personal_index/dashboard/stats.py: StatsCollector
- personal_index/export_markdown.py: pathlib.Path
- personal_index/utils/__init__.py: typing.Optional
- personal_index/config/__init__.py: typing.Optional
- personal_index/crawler/__init__.py: typing.Optional
- And many more...

### Unused Variables (F841)
Fixed in:
- personal_index/auth/passwords.py: cfg variable
- personal_index/content_dedup.py: tokens1, best_url
- personal_index/index.py: tokens, text
- personal_index/search_index.py: page, text
- personal_index/tags.py: removed

### Broken Imports
- personal_index/dashboard/__init__.py tried to import StatsCollector from dashboard.stats instead of personal_index.stats
- Fixed by importing from correct module

## Impact
- Runtime errors when using affected modules
- Import failures in some cases
- Code quality issues (dead code, unused variables)

## Suggestion
All issues have been fixed. Run `ruff check personal_index/` to verify no F401/F821/F841 issues remain.
