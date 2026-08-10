# TICKET-79: Use dictionary instead of consecutive `if` statements (SIM116)

## Title
Consecutive `if` statements assigning to the same key can be replaced with a dictionary

## Evidence
ruff SIM116 flags 1 location:

1. `personal_index/content_type.py:271` — consecutive `if` statements assigning to the same dict key

Example pattern:
