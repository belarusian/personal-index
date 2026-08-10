# TICKET-37: Liskov violation — `PriorityLevel` overrides `__gt__`/`__lt__` with incompatible parameter types

## Title
`PriorityLevel.__gt__` and `__lt__` violate Liskov substitution principle by narrowing parameter type from `str` to `PriorityLevel`

## Evidence
In `personal_index/content_priority.py:15-39`:
