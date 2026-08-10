# TICKET-102: Dead code — `get_pinned_content` and `is_content_pinned` are never called

## Title
Two public functions in `content_pin.py` are defined but never imported or called anywhere in the codebase

## Evidence
`personal_index/content_pin.py` defines two module-level functions that are never used:

1. **Line 176**: `is_content_pinned(item_id: str) -> bool` — wraps `_get_default_pinner().is_pinned(item_id)`
2. **Line 188**: `get_pinned_content() -> List[PinnedItem]` — wraps `_get_default_pinner().get_pinned_items()`

Neither function appears in any import statement across the entire `personal_index/` package or `tests/` directory:
