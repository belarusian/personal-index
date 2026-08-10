# TICKET-55: Type error — migrations/base.py uses importlib.util without importing it

## Title
migrations/base.py references `importlib.util` but only imports `importlib`, causing mypy errors

## Evidence
`personal_index/migrations/base.py:5`:
