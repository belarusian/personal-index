# TICKET-250: content_scheduler cron day-of-month / day-of-week combined with AND instead of OR

Status: RESOLVED (merged to main, cycle 4, gh #329 closed)
Module: personal_index/content_scheduler.py
Issue: #329

## Symptom
Standard cron semantics: when BOTH the day-of-month (dom) and day-of-week (dow)
fields are restricted (neither is `*`), a matching day is one that satisfies
dom OR dow. This module always combines them with AND, so a task like
`0 0 1 * 1` (at 00:00 on the 1st of the month OR on Monday) only fires on days
that are BOTH the 1st AND a Monday.

## Evidence
- `personal_index/content_scheduler.py:110-112` (`_compute_next_run`):
  `candidate.day in self._dom and ... and candidate.weekday() in self._dow`
  - the dom and dow checks are joined with `and` unconditionally.
- Reproduction (verified on main, HEAD 4dc0bfa):
  `ScheduledTask('t1','n','crawl','0 0 1 * 1')` -> `_dom=[1]`, `_dow=[0]`,
  `next_run=2027-02-01` (the next day that is both the 1st and a Monday).
  Over 365 days: AND matches = 2, OR (correct) matches = 62.
- The module is public API: `personal_index/__init__.py` exports
  `ScheduledTask` / `TaskScheduler`.

## Minimal additive fix
Track whether the raw dom and dow fields were restricted (not `*`). In
`_compute_next_run`, when both are restricted, match on
`(day in dom) OR (weekday in dow)`; otherwise keep the existing AND of the
individual checks. Add a test asserting `0 0 1 * 1` schedules on a Monday that
is not the 1st (i.e. next_run is a Monday, not the next 1st-and-Monday).
