# TICKET-533: ContentRollback.clear docstring + pinning test

Status: RESOLVED
File: personal_index/content_rollback.py
Symptom: ContentRollback.clear (def at line 48) has a terse docstring
  ("Clear rollback points.") that does not state its two-path contract.
  The method branches on the url argument: when url is truthy it pops only
  that url's rollback points (self._rollback_points.pop(url, None)); when
  url is falsy (None) it clears ALL urls (self._rollback_points.clear()).
  Sibling method rollback already carries an exact-contract docstring
  (TICKET-320); clear is the remaining un-documented public method.

Evidence (verified in code + TestContentRollback):
  - clear(url): if url: self._rollback_points.pop(url, None)
                else:   self._rollback_points.clear()
  - test_clear_specific_url pins: after clear("http://example.com"),
    example.com has 0 points, other.com still has 1.
  - test_clear_all pins: after clear() (no arg), example.com has 0 points.

Minimal additive fix:
  - Add an exact-contract docstring to clear stating the two-path behavior
    (url truthy -> pop that url only; url falsy/None -> clear all urls) and
    that it is a pure mutation of the internal store (no return value).
  - Add pinning test TestClearDocstring532 mirroring the
    TestGetStatsDocstring531 pattern, asserting key phrases present
    (pop, clear, url, None).

Issue: #941
