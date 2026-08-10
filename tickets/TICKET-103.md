# TICKET-103: Type annotation mismatch — `Keyword.positions` declared as `List[int]` but defaults to `None`

## Title
`personal_index/keyword_extractor.py` declares `positions: List[int] = None` which is a type error

## Evidence
`personal_index/keyword_extractor.py`, line 19:
