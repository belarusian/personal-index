Status: IN PROGRESS (cycle 194: extract_top_n negative guard in progress)
Kind: QA
Issue: #1028
Deep test: tests/deep/test_keyword_extractor_adversarial.py::test_extract_top_n_negative (xfail-strict)

# QA-1: extract_top_n leaks Python negative-slice semantics for out-of-range n

## Symptom
`KeywordExtractor.extract_top_n(text, n)` is documented as "Extract top N
keywords as plain strings." For an out-of-range negative `n` (e.g. `n=-1`) it
returns `keywords[:-1]` - i.e. ALL keywords except the last one - instead of
an empty list. `n=0` correctly returns `[]`, so the guard is missing only for
negative values.

## Exact repro