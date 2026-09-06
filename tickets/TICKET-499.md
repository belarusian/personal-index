# TICKET-499: UrlFilter.get_matching_rule docstring omits its exact contract

## File
personal_index/url_filter.py

## Function
UrlFilter.get_matching_rule (line ~104)

## Symptom
The docstring reads only `"""Get the first matching rule for a URL, or None."""`
— a generic claim that omits the actual observable contract:
- the WHITELIST is scanned first (whitelist takes precedence over blacklist);
  only if no whitelist rule matches is the BLACKLIST scanned
- within each list, rules are scanned in insertion order and the FIRST matching
  rule is returned
- returns the ACTUAL stored `UrlFilterRule` object (identity, not a copy)
- returns `None` when neither list has a matching rule (including an empty filter)
- pure accessor: does not mutate `_whitelist` or `_blacklist`

## Evidence (verified live)
- url matching only a blacklist rule -> returns that rule (is_blacklist True)
- url matching BOTH a whitelist and a blacklist rule -> returns the WHITELIST
  rule (is_blacklist False), even when the blacklist rule was added first
- two whitelist rules matching -> the first one added is returned
- no matching rule (or empty filter) -> None
- returned rule `is` the stored rule object (identity preserved)

## Minimal additive fix
Reword the `get_matching_rule` docstring to state the exact contract above, and
append pinning tests to tests/test_url_filter.py pinning: whitelist precedence
over blacklist, first-in-insertion-order within a list, identity (returns the
stored object, not a copy), None when no match / empty filter, and no mutation.

## Status
OPEN

Issue: #854
