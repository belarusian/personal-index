# TICKET-003: mypy error — incompatible assignment `None` to `list[str]` in handler

**File:** `personal_index/content_router/handler.py:20`

**What's wrong:**
The dataclass field `supported_types` is declared as `list[str]` but assigned `None` as default.

**Evidence:**
