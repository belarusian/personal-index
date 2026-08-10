# TICKET-29: Type error — `InterestStore._load()` passes `datetime` to `Interest.created_at` which expects `str`

## Title
`interest_store.py` constructs `Interest` with `created_at=datetime.utcnow()` but `models.Interest.created_at` is typed as `str`

## Evidence
In `personal_index/interest_store.py:55-64`:
