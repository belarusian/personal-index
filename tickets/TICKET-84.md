# TICKET-84: Type error — `Keyword.positions` default is `None` but typed as `List[int]`

## Title
`Keyword.positions` has incompatible default `None` for type `List[int]`

## Evidence
File: `personal_index/keyword_extractor.py`
Line 19: `positions: List[int] = None  # positions in text`

mypy flags: `personal_index/keyword_extractor.py:19: error: Incompatible types in assignment (expression has type "None", variable has type "list[int]")  [assignment]`

The `__post_init__` method (lines 21-23) handles the `None` → `[]` conversion, but the type annotation itself is wrong.

## Impact
Type checkers will flag this as an error. Runtime behavior is correct due to `__post_init__`, but the type annotation misleads consumers and static analysis tools.

## Suggestion
Change line 19 to:
