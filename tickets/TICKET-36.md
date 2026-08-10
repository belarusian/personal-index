# TICKET-36: Type error — `summarizer.py` mixes `int` and `float` in `sentence_scores` tuples

## Title
`summarizer.py` appends tuples with inconsistent types: `(int, int, str)` vs `(float, int, str)`

## Evidence
In `personal_index/summarizer.py:101-108`:
