# TICKET-251: content_scheduler cron day-of-week field rejects `7` (Sunday alias)

Status: OPEN
Module: personal_index/content_scheduler.py
Symptom: A cron expression whose day-of-week field uses `7` (the standard-cron
alias for Sunday, equivalent to `0`) is silently dropped, so the task never
schedules (next_run stays None).

Evidence (reproduced on main):
- `ScheduledTask('t','n','crawl','0 0 * * 7')` -> `_dow == []`, `next_run is None`.
- `ScheduledTask('t','n','crawl','0 0 * * 0')` -> `_dow == [6]`, `next_run` set (Sunday).
- Root cause: `_parse_cron` calls `self._parse_field(dow, 0, 6)`; `_parse_field`
  filters `v for v in values if min_val <= v <= max_val`, so `7` is excluded.
  Standard cron (POSIX / Vixie) defines the DOW field as 0-7 where both 0 and 7
  mean Sunday.

Fix (minimal, additive): in `_parse_cron`, map cron DOW value `7` to `0` before
parsing (e.g. normalize the dow field so `7` becomes `0`), or post-process the
parsed cron_dow list to fold `7` into `0`. Keep the existing 0->6 / n->n-1
Python-weekday conversion. Add tests: `test_cron_dow_7_is_sunday` (next run is a
Sunday, matches the dow=0 result) and `test_cron_dow_7_in_range` (e.g. `0 0 * * 6-7`
schedules on Saturday and Sunday).

Issue: #331
