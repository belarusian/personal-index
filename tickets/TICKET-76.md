# TICKET-76: Return condition directly instead of if-else (SIM103)

## Title
Functions use `if`-`else` to return `True`/`False` when the condition can be returned directly

## Evidence
ruff SIM103 flags 4 locations:

1. `personal_index/auth/sessions.py:41` — `if cond: return True; else: return False`
2. `personal_index/domains.py:128` — `if cond: return True; else: return False`
3. `personal_index/domains.py:131` — `if cond: return True; else: return False`
4. `personal_index/link_analyzer.py:109` — `if cond: return True; else: return False`
5. `personal_index/robots_cache.py:46` — `if cond: return True; else: return False`

Example pattern:
