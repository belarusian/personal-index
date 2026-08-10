# TICKET-53: Type error — content_priority.py PriorityLevel.__gt__/__lt__ override incompatible with str supertype

## Title
PriorityLevel inherits from str and Enum, but __gt__/__lt__ have incompatible parameter types

## Evidence
`personal_index/content_priority.py:15-39`:
