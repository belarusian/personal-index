# TICKET-12: Missing function-level docstrings on public functions

## Title
65 public functions across the codebase lack docstrings

## Evidence
Static analysis of all modules in `personal_index/` reveals 65 public functions (non-`_` prefixed) without docstrings. Examples:

| File | Line | Function |
|------|------|----------|
| `api/handlers.py` | 81 | `timed_send` |
| `api/handlers.py` | 105 | `ensure_json_type` |
| `api/middleware.py` | 32 | `capture_send` |
| `api/middleware.py` | 85 | `add_cors_headers` |
| `api/middleware.py` | 121 | `add_request_id` |
| `api/models.py` | 20 | `to_dict` |
| `api/models.py` | 38 | `ok` |
| `api/models.py` | 42 | `error` |
| `api/pagination.py` | 22 | `start_index` |
| `api/pagination.py` | 26 | `end_index` |
| `auth/api_keys.py` | 30 | `to_dict` |
| `auth/sessions.py` | 24 | `to_dict` |
| `auth/tokens.py` | 25 | `to_dict` |
| `cache.py` | 259 | `wrapper` |
| `cli.py` | 285 | `save` |
| `config/__init__.py` | 26-83 | Multiple `to_dict`/`from_dict` |

All modules have module-level docstrings (confirmed), but function-level coverage is incomplete.

## Impact
- API.md documentation may be incomplete or inaccurate
- IDE auto-completion lacks function descriptions
- New contributors cannot easily understand function purpose
- `to_dict`/`from_dict` methods are particularly important for API consumers

## Suggestion
1. Add docstrings to all 65 public functions
2. Prioritize `to_dict`/`from_dict` methods as they define serialization contracts
3. Add a linting rule (e.g., `ruff` with `D103` or `pydocstyle`) to enforce docstrings
4. Consider using a docstring template (Google, NumPy, or Sphinx style) consistently
