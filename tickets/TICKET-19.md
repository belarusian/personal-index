# TICKET-19: F811 naming conflict in personal_index/api/models.py

## Title
`error` is both a dataclass field and a classmethod in `APIResponse`

## Evidence
In `personal_index/api/models.py`, the `APIResponse` class defines:
- Line 16: `error: str | None = None` — a dataclass field
- Line 42: `def error(cls, message: str, error_code: str | None = None)` — a classmethod

Ruff reports: `F811 Redefinition of unused 'error' from line 16`
