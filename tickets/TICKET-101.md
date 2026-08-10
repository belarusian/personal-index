# TICKET-101: Prefer `str.removeprefix()` over conditional slice in `url_dedup.py` (FURB188)

## Title
Three instances of `if domain.startswith("www."): domain = domain[4:]` should use `str.removeprefix("www.")`

## Evidence
`personal_index/url_dedup.py` contains three identical patterns that can be simplified:

1. Line 102-103:
