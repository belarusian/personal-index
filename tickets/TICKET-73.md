# TICKET-73: Unnecessary assignment before `return` (RET504)

## Title
Variables assigned immediately before `return` — the value can be returned directly

## Evidence
ruff RET504 flags 4 locations:

1. `personal_index/encoding.py:97` — `text = ...; return text`
2. `personal_index/filter/engine.py:99` — `result = ...; return result`
3. `personal_index/filter/matcher.py:69` — `score = ...; return score`
4. `personal_index/utils/__init__.py:63` — `text = ...; return text`

Example from `personal_index/encoding.py:97`:
