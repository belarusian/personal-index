Status: OPEN
Kind: QA
Issue: #1165
Deep test: tests/deep/test_link_analyzer_adversarial.py (TestNegativeMaxAnchorLength, 2 xfail-strict)

# QA-9: link_analyzer.analyze — negative max_anchor_length corrupts anchor text

## Symptom
`LinkAnalyzer.__init__(max_anchor_length=...)` does not guard an out-of-range
(negative) `max_anchor_length`. In `_analyze_single_link`, anchor text is
truncated with `a[:self.max_anchor_length]`. With a negative N this is a
Python negative slice that **drops the last N characters** instead of
clamping to a non-negative bound:

- `max_anchor_length=-1`, anchor `"hello"` -> `"hell"` (last char dropped).
- `max_anchor_length=-2`, anchor `"hello world"` -> `"hello wor"` (last 2 dropped).

A negative bound is a caller error that should behave like `0` (anchor
stripped to `''` -> not counted), matching the `max_anchor_length=0` path.
Instead it silently corrupts the anchor text that feeds
`stats.anchor_text_distribution` and `top_anchor_texts`.

This is a distinct defect from the QA-5/QA-6 negative-bound classes: it is a
string-truncation clamp in `personal_index/link_analyzer.py`, not a `list[:N]`
top-N slice (QA-5) or a snippet windowing bound (QA-6).

## Affected site
| module | function | line | idiom |
|--------|----------|------|-------|
| link_analyzer.py | `LinkAnalyzer._analyze_single_link` | ~100 | `a[:self.max_anchor_length]` (negative N -> drop-last-N) |

## Exact repro
    python3 -c "
    from personal_index.link_analyzer import LinkAnalyzer
    a = LinkAnalyzer(base_domain='example.com', max_anchor_length=-1)
    r = a.analyze('http://example.com/', [{'url':'http://ext.com/x','text':'hello'}])
    print('max_anchor_length=-1  :', r.stats.anchor_text_distribution)
    a2 = LinkAnalyzer(base_domain='example.com', max_anchor_length=-2)
    r2 = a2.analyze('http://example.com/', [{'url':'http://ext.com/x','text':'hello world'}])
    print('max_anchor_length=-2  :', r2.stats.anchor_text_distribution)
    a0 = LinkAnalyzer(base_domain='example.com', max_anchor_length=0)
    r0 = a0.analyze('http://example.com/', [{'url':'http://ext.com/x','text':'hello'}])
    print('max_anchor_length=0   :', r0.stats.anchor_text_distribution)
    "

## Observed output
    max_anchor_length=-1  : {'hell': 1}
    max_anchor_length=-2  : {'hello wor': 1}
    max_anchor_length=0   : {}

`max_anchor_length=-1` yields `{'hell': 1}` (corrupted) instead of `{}` (the
`0` behaviour).

## Expected per docs/contract
The `analyze` docstring says anchor text is "stripped and truncated to
``max_anchor_length`` before counting". A negative bound is out-of-range and
must be clamped to a non-negative bound (consistent with the `0` behaviour),
never dropping the trailing characters of the anchor.

## Deep test
tests/deep/test_link_analyzer_adversarial.py::TestNegativeMaxAnchorLength
(2 xfail-strict tests pin the correct contract; they flip to hard passes once
the implementer clamps `max_anchor_length = max(0, max_anchor_length)`).
