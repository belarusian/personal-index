# TICKET-68: Unsorted `__all__` in auth/__init__.py (RUF022)

## Title
`__all__` in `personal_index/auth/__init__.py` is not sorted, violating ruff RUF022

## Evidence
ruff RUF022 flags 1 location:

1. `personal_index/auth/__init__.py:29` — `__all__` is not sorted

Current order groups by submodule (tokens, api_keys, permissions, passwords, sessions), but ruff expects alphabetical order:
