# TICKET-89: Type error — `PriorityLevel.__gt__` and `__lt__` violate Liskov substitution principle

## Title
`PriorityLevel` inherits from `str` but overrides `__gt__`/`__lt__` with incompatible parameter types

## Evidence
File: `personal_index/content_priority.py`
Lines 34-40:
