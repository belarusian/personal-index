Status: IMPLEMENTED 2026-09-09
Kind: QA
Issue: #1139
Deep test: tests/deep/test_results_adversarial.py (TestCreateSnippetNegativeMaxLength, 2 xfail-strict)

# QA-6: results.create_snippet — negative max_length produces garbage snippet

## Symptom
`ResultsFormatter.create_snippet(text, query, max_length)` does not guard an
out-of-range (negative) `max_length`. A negative bound is a caller error that
should be clamped to a non-negative bound (matching the `0` behaviour), but
instead the window arithmetic produces a garbage snippet:

- query FOUND: `end = min(len(text), idx + len(query) + max_length)` collapses
  to before `start`, so `snippet = text[start:end]` is empty and the two
  ellipsis branches both fire -> the result is the literal string `'...'`.
- query NOT FOUND: `return text[: max_length + 50]` with `max_length=-100`
  gives `text[:-50]` (all-but-last-50) -> for a short text this is `''`.

This is a distinct defect from the QA-5 negative-slice "top N / limit" leak
class: it is a windowing-bound clamp, not a `list[:N]` top-N slice, and it
lives in `personal_index/results.py` (not one of the 9 QA-5 sites).

## Affected site
| module | function | line | idiom |
|--------|----------|------|-------|
| results.py | `ResultsFormatter.create_snippet(text, query, max_length)` | ~55-70 | `end = min(len(text), idx + len(query) + max_length)` / `text[: max_length + 50]` |

## Exact repro
    python3 -c "
    from personal_index.results import ResultsFormatter
    f = ResultsFormatter()
    print('found   :', repr(f.create_snippet('hello world', 'world', -100)))
    print('notfound:', repr(f.create_snippet('hello world', 'zzz', -100)))
    print('zero    :', repr(f.create_snippet('hello world', 'world', 0)))
    "

## Observed output
    found   : '...'
    notfound: ''
    zero    : 'hello world'

`max_length=-100` yields `'...'` (found) / `''` (not found) instead of a sane
bounded snippet.

## Expected per docs/contract
The docstring says "The window is bounded by ``max_length`` when given
explicitly". A negative bound is out-of-range and must be clamped to a
non-negative bound (consistent with the `0` behaviour), never producing a lone
ellipsis or an empty string for a non-empty text.

## Deep test
tests/deep/test_results_adversarial.py::TestCreateSnippetNegativeMaxLength
(2 xfail-strict tests pin the correct contract; they flip to hard passes once
the implementer clamps `max_length = max(0, max_length)`).
