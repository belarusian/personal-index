# TICKET-85: Type error — `KeywordExtractor.extract()` reassigns `Counter` to plain `dict`

## Title
`freq` variable re-typed from `Counter[str]` to `dict[str, int]` in `KeywordExtractor.extract()`

## Evidence
File: `personal_index/keyword_extractor.py`
Line 48: `freq = Counter(tokens)` — `freq` is inferred as `Counter[str]`
Line 49: `freq = {k: v for k, v in freq.items() if v >= self.min_frequency}` — `freq` is now `dict[str, int]`

mypy flags: `personal_index/keyword_extractor.py:49: error: Incompatible types in assignment (expression has type "dict[str, int]", variable has type "Counter[str]")  [assignment]`

## Impact
This is a variable reassignment type change. While Python allows it at runtime, mypy flags it because the variable `freq` was first inferred as `Counter[str]` and then reassigned to `dict[str, int]`. This can confuse static analysis and IDE type hints.

## Suggestion
Use a different variable name for the filtered dict, or use `Counter` constructor with filtering:
