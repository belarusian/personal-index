# TICKET-75: Unnecessary list comprehension (C416) and import sorting issues (I001)

## Title
Unnecessary list comprehension in serializer.py and unsorted import blocks in 3 modules

## Evidence
ruff C416 flags 1 location:
1. `personal_index/serializer.py:79` — `list([...])` should be `[...]`

ruff I001 flags 3 locations:
1. `personal_index/api/pagination.py:3` — import block un-sorted
2. `personal_index/api/rate_limit_middleware.py:3` — import block un-sorted
3. `personal_index/auth/tokens.py:3` — import block un-sorted

## Impact
- `list([...])` is redundant — the list literal already creates a list
- Unsorted imports violate PEP 8 / isort conventions

## Suggestion
1. Replace `list([...])` with `[...]`
2. Run `ruff --fix --select=I001` to sort imports
