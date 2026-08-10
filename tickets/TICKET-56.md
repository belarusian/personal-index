# TICKET-56: Type error — api/rate_limit_middleware.py calls .append() on immutable Sequence

## Title
rate_limit_middleware.py calls .append() on a Sequence[str], which may be immutable

## Evidence
`personal_index/api/rate_limit_middleware.py:142`:
