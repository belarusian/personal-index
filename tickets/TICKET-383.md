# TICKET-383: throttle.py placeholder docstrings do not describe behavior

Status: OPEN
Issue: #604

## File
personal_index/throttle.py

## Symptom
Several public methods and one property carry placeholder docstrings that
do not describe what the code actually does. These are class-(b) doc-drift:
the docstring is a stub, so a reader cannot learn the contract from it.

## Evidence (line numbers)
- L23 ThrottleRule.rate_per_second -> """Rate_per_second."""
- L49 ThrottleManager.set_rule -> """Process set_rule.\n\nArgs:\n domain, rule.\n"""
- L57 ThrottleManager.get_rule -> """Process get_rule.\n\nArgs:\n domain.\n"""
- L65 ThrottleManager.should_throttle -> """Process should_throttle.\n\nArgs:\n url.\n"""
- L117 ThrottleManager.get_stats -> """Process get_stats.\n\nArgs:\n domain.\n"""

## Minimal additive fix
Reword each placeholder docstring to state the EXACT behavior the body
performs (enumerate the fields / the domain-extraction + window-pruning +
count-vs-max conditional / the per-domain vs aggregate stats the code
returns). Add ONE behavior test that pins the corrected claims against the
returned objects (rate_per_second value, should_throttle True/False across
the max_requests boundary, get_stats per-domain vs aggregate keys) so the
fix is witnessed as doc-only.

## Notes
- No behavior change; docstrings only + one pinning test.
- Verified ticket number 383 is free before committing (382 was the last).
