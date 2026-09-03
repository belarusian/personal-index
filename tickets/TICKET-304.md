# TICKET-304: read_time_minutes annotated -> float but returns int

- Status: OPEN
- Module: personal_index/text_utils.py
- Defect class: (b) doc/behavior drift
- Issue: #441

## Symptom
`read_time_minutes` is annotated `-> float`, but the body returns an int:
`round(x)` with no ndigits returns an int, and `max(1, int)` is an int.
The code is correct (whole minutes, minimum 1); the annotation is the drift.
A caller trusting the annotation (or mypy) will treat the result as a float.

## Evidence
- Site: personal_index/text_utils.py:272 - `def read_time_minutes(text: str, wpm: int = 200) -> float:`
- Body: `return max(1, round(words / wpm))` (line 283) - int.
- Runtime: `read_time_minutes('word '*400)` -> `2` (int); `read_time_minutes('hello')` -> `1` (int).
- Caller: personal_index/content_enricher.py:97 `enriched.reading_time = read_time_minutes(text)`
  where `EnrichedContent.reading_time: float = 0.0` (line 24). int is assignable to float,
  so no caller change is required.

## Fix (minimal, honest)
Change the return annotation `-> float` to `-> int`. Do NOT change the code to
return a float (that would change behavior). Tighten the Returns docstring line
to say it returns an integer number of minutes (minimum 1). Add regression tests
pinning the return type (isinstance int / type is int) in tests/test_text_utils.py.
