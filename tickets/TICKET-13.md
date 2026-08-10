# TICKET-13: Widespread unused imports across 30+ modules

## Title
Over 50 unused imports detected across the codebase, including standard library, typing, and cross-module imports

## Evidence
Static analysis confirmed the following truly unused imports (not used in code or type annotations):

### Standard Library Unused Imports
| File | Line | Unused Import |
|------|------|---------------|
| `personal_index/content_health.py:17` | `import time` | Never called |
| `personal_index/content_priority.py:7` | `import re` | Never called |
| `personal_index/content_priority.py:9` | `from datetime import timedelta` | Never used |
| `personal_index/content_type.py:7` | `import re` | Never called |
| `personal_index/fuzzy_search.py:7` | `import re` | Never called |
| `personal_index/keyword_extractor.py:7` | `import re` | Never called |
| `personal_index/link_analyzer.py:9` | `from collections import defaultdict` | Never used |
| `personal_index/export.py:7` | `import os` | Never called |
| `personal_index/dashboard/aggregator.py:8` | `from datetime import timezone` | Never used |
| `personal_index/content_linker/linker.py:8` | `from datetime import timedelta` | Never used |
| `personal_index/content_timeline/timeline_view.py:6` | `from datetime import datetime, timezone, timedelta` | None used |

### Typing Unused Imports
| File | Line | Unused Import |
|------|------|---------------|
| `personal_index/backup.py:10` | `from typing import Set` | Never used |
| `personal_index/cache.py:10` | `from typing import Generic` | Never used |
| `personal_index/content_extractor.py:10` | `from typing import Optional` | Never used |
| `personal_index/content_scheduler.py:10` | `from typing import Set` | Never used |
| `personal_index/fuzzy_search.py:9` | `from typing import Optional` | Never used |
| `personal_index/keyword_extractor.py:9` | `from typing import Optional` | Never used |
| `personal_index/api/middleware.py:8-9` | `from typing import Callable, Dict` | Never used |
| `personal_index/api/pagination.py:8-9` | `from typing import Any, Optional` | Never used |
| `personal_index/api/server.py:9` | `from typing import Dict` | Never used |
| `personal_index/config/models.py:9` | `from typing import Optional` | Never used |
| `personal_index/export.py:12` | `from typing import Dict` | Never used |
| `personal_index/importer.py:10` | `from typing import Dict` | Never used |
| `personal_index/notifications.py:9` | `from typing import Optional` | Never used |
| `personal_index/pipeline.py:9` | `from typing import Any` | Never used |
| `personal_index/sitemap.py:9` | `from typing import Dict` | Never used |
| `personal_index/tfidf.py:9` | `from typing import Optional` | Never used |
| `personal_index/url_dedup.py:10` | `from typing import Set` | Never used |
| `personal_index/webhook.py:9` | `from typing import Optional` | Never used |

### Cross-Module Unused Imports
| File | Line | Unused Import |
|------|------|---------------|
| `personal_index/content_categorizer.py:13` | `from personal_index.text_utils import STOPWORDS` | Never used |
| `personal_index/keyword_extractor.py:14` | `from personal_index.text_utils import STOPWORDS` | Never used |
| `personal_index/dashboard/stats.py:38` | `from personal_index.stats import StatsCollector` | Never used |
| `personal_index/content_timeline/timeline_view.py:11` | `from personal_index.content_timeline.timeline_entry import TimelineEntry` | Never used |
| `personal_index/migrations/runner.py:9` | `from personal_index.migrations.base import BaseMigration` | Never used |
| `personal_index/export.py:14` | `from bookmarks import Bookmark` | Wrong module (should be `.bookmarks`) |

### Dataclass Unused Imports
| File | Line | Unused Import |
|------|------|---------------|
| `personal_index/content_versioning.py:10` | `from dataclasses import field` | Never used |
| `personal_index/api/models.py:8` | `from dataclasses import asdict` | Never used |
| `personal_index/serializer.py:8` | `from dataclasses import asdict` | Never used |

## Impact
- Clutters code and misleads readers about dependencies
- `from bookmarks import Bookmark` in `export.py` is a BROKEN import — should be `from .bookmarks import Bookmark`
- Increases import time and memory footprint
- Makes it harder to spot genuinely needed imports

## Suggestion
1. Remove all confirmed unused imports
2. Fix `export.py:14` — change `from bookmarks import Bookmark` to `from .bookmarks import Bookmark` (or remove if unused)
3. Add a linting rule (ruff `F401`) to prevent future unused imports
4. Run `ruff check --select F401 personal_index/` as a pre-commit hook
