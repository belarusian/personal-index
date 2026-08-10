# TICKET-26: Type error — `matched_indices` default `None` conflicts with `List[int]` annotation

## Title
Dataclass fields default to `None` but are annotated as non-optional `List[int]`

## Evidence
In `personal_index/fuzzy_search.py:15`:
