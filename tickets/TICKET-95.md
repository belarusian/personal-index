# TICKET-95: Broad exception handling — `except Exception` swallows errors silently

## Title
Multiple modules use bare `except Exception` that silently swallows errors, making debugging difficult

## Evidence
File: `personal_index/export_markdown.py`
Line 323: `except Exception: return False`

The `export_to_file()` function catches all exceptions and returns `False` without logging. This means any error (file permission issues, encoding errors, data corruption) is silently ignored.

File: `personal_index/content_health.py`
Line 456: `except Exception: return False`

The `is_valid_url()` function catches all exceptions from `urlparse()`. Since `urlparse()` is a pure function that shouldn't raise exceptions for string inputs, this is unnecessary and masks potential bugs.

## Impact
- `export_markdown.py`: Failed exports are silently ignored. Users won't know why their export failed.
- `content_health.py`: If `urlparse()` ever raises an unexpected exception (e.g., due to a bug or edge case), it will be silently swallowed.

## Suggestion
1. `export_markdown.py:323`: Add logging before returning `False`:
