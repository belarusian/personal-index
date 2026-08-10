# TICKET-27: Type error — `best_len` variable is `int` but assigned `float` in fuzzy_search.py

## Title
Variable `best_len` typed as `int` (via `= 0`) but assigned a `float` from `SequenceMatcher.ratio()`

## Evidence
In `personal_index/fuzzy_search.py:132-137`:
