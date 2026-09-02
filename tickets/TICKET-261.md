# TICKET-261: non-string element in `Interest.url_patterns` crashes `Interest.matches` and `InterestStore.get_all_url_patterns`

Status: RESOLVED (merged to main, gh #351 closed)

## File
- `personal_index/models.py` — `Interest.matches` (url_patterns loop, line 104)
- `personal_index/interests.py` — `InterestStore.get_all_url_patterns` (line 97)

## Symptom
A non-string element (int, None) in an `Interest.url_patterns` list crashes URL matching:
- `Interest.matches(text, url)` raises `TypeError: argument of type 'int' is not iterable`
  (from `"*" in pattern` at models.py:109). The surrounding `try/except re.error` does NOT
  catch `TypeError`, so the exception propagates.
- `InterestStore.get_all_url_patterns()` raises `TypeError: first argument must be string
  or compiled pattern` (from `re.compile(pattern_str)` at interests.py:103).

## Evidence
- Reproduced live: `Interest(name='x', url_patterns=[1, 'valid', None]).matches('hello', url='http://example.com')`
  -> `TypeError: argument of type 'int' is not iterable`.
- Reproduced live: `InterestStore` with `Interest(name='x', url_patterns=[1, 'valid'])`
  -> `get_all_url_patterns()` -> `TypeError: first argument must be string or compiled pattern`.
- Consistency tell: the `keywords` loop (models.py:99) and `topics` loop (models.py:102)
  both carry `isinstance(..., str)` guards added in TICKET-259, but the `url_patterns`
  loop (models.py:104) was left unguarded. Same systemic defect class
  (`isinstance`-guard-missing-on-a-bare-list-field).

## Minimal additive fix
- models.py `Interest.matches`: add `if not isinstance(pattern, str): continue` at the top
  of the `for pattern in self.url_patterns:` loop body.
- interests.py `get_all_url_patterns`: add `if not isinstance(pattern_str, str): continue`
  at the top of the inner loop body.
- Add regression tests for both paths (non-string int + None elements).

## Issue
Issue: #351
