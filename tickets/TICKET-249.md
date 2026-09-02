# TICKET-249: content_scheduler cron range-with-step crashes

Status: RESOLVED
Issue: #327
Module: personal_index/content_scheduler.py
Symptom: A valid cron expression using a range with a step (e.g. `0 9-17/2 * * 1-5`)
raises an unhandled ValueError at construction, so the task can never be scheduled.
Evidence: `_parse_field` (content_scheduler.py:86-92) does `start = int(base)` where
base can be a range like "9-17"; `int("9-17")` -> ValueError. Reproduced:
  ScheduledTask('t1','n','crawl','0 9-17/2 * * 1-5') -> ValueError: invalid literal for int() with base 10: '9-17'
Existing tests cover `*/5` (step, star base) and `9-17` (range, no step) but not range-with-step.
Minimal additive fix: in the `"/" in part` branch, when base contains "-" parse it as a
start-end range; otherwise treat base as a start value with end=max_val. Add a test for
`0 9-17/2 * * 1-5` asserting next_run is not None.
