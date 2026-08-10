# TICKET-48: Broad exception handling — 12 additional modules catch Exception silently

## Title
12 additional functions catch Exception broadly and silently, not covered by TICKET-45

## Evidence
TICKET-45 covers broad exception handling in url_utils.py, content_health.py, and export_markdown.py. However, 12 additional locations were found:

1. personal_index/api/handlers.py:40 — catches Exception
2. personal_index/content_categorizer.py:559 — catches Exception
3. personal_index/content_linker/linker.py:20 — catches Exception
4. personal_index/content_scheduler.py:180 — catches Exception
5. personal_index/importer.py:106 — catches Exception
6. personal_index/importer.py:131 — catches Exception
7. personal_index/importer.py:220 — catches Exception
8. personal_index/migrations/base.py:153 — catches Exception
9. personal_index/notifications.py:250 — catches Exception
10. personal_index/pipeline.py:27 — catches Exception
11. personal_index/pipeline.py:99 — catches Exception
12. personal_index/url_history.py:130 — catches Exception

## Impact
- Swallows unexpected errors (e.g., KeyboardInterrupt, MemoryError, bugs)
- Makes debugging difficult — root cause of failures is hidden
- Violates principle of least surprise — callers cannot know if operation succeeded

## Suggestion
Replace broad except Exception with specific exception types (e.g., ValueError, KeyError, OSError). If broad catching is intentional, add logging at minimum:

    except Exception as e:
        logger.error("Unexpected error: %s", e)
        raise
