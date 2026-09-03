# TICKET-314: url_utils.urls_are_equivalent reports two different non-http/https URLs as equivalent

- Status: RESOLVED (cycle 66, PR #464, gh #462 closed)
- Module: personal_index/url_utils.py
- Defect class: (b) doc/behavior drift — docstring promises "equivalent after normalization" but the body conflates all non-normalizable URLs
- Issue: #462

## Symptom
`urls_are_equivalent(url1, url2)` (url_utils.py:189) returns
`normalize_url(url1) == normalize_url(url2)`. `normalize_url` returns `None`
for any URL whose scheme is not http/https (and for empty input). Therefore two
*distinct* non-http/https URLs both normalize to `None` and compare equal, so the
function reports them as "equivalent" — contradicting its docstring.

## Evidence (verified at runtime, cycle 66)
- `urls_are_equivalent("mailto:a@x.com", "mailto:b@y.com")` -> True  (different URLs!)
- `urls_are_equivalent("ftp://a.com/f", "ftp://b.com/g")`    -> True  (different URLs!)
- `urls_are_equivalent("", "")`                              -> True  (both None)
Existing tests (tests/test_url_utils.py:294-307) only exercise http/https, so no
test pins the buggy behavior.

## Fix (minimal, additive)
In `urls_are_equivalent`, treat a `None` normalization as "not equivalent":
    n1 = normalize_url(url1)
    n2 = normalize_url(url2)
    if n1 is None or n2 is None:
        return False
    return n1 == n2
Add regression tests for the two distinct non-http/https URLs and for empty input.
