# TICKET-252: content_scheduler ScheduledTask constructor raises on malformed cron field content

Status: RESOLVED (merged to main, gh #333 closed)
Module: personal_index/content_scheduler.py
Symptom: A 5-field cron expression whose field *content* is malformed (e.g. a
zero step `*/0`, a non-numeric token `abc`) makes the `ScheduledTask`
constructor raise `ValueError` instead of degrading gracefully to
`next_run = None`. The module's own design treats malformed input as "never
runs" (see `test_cron_invalid`), but that only holds for the wrong-field-count
case; a well-formed 5-field expression with bad content crashes the caller.

Evidence (reproduced on main):
- `ScheduledTask('t','n','crawl','*/0 * * * *')` -> raises `ValueError: range() arg 3 must not be zero`.
- `ScheduledTask('t','n','crawl','5/0 * * * *')` -> raises `ValueError: range() arg 3 must not be zero`.
- `ScheduledTask('t','n','crawl','abc * * * *')` -> raises `ValueError: invalid literal for int() with base 10: 'abc'`.
- Contrast: `ScheduledTask('t','n','crawl','invalid')` (1 field) -> `next_run is None` (no raise).
- Root cause: `_parse_field` calls `int(...)` and `range(start, end+1, step)`
  with no guard; `_parse_cron` does not catch the resulting `ValueError`.

Fix (minimal, additive): in `_parse_cron`, wrap the field-parsing block
(minute/hour/dom/month/dow) in `try/except ValueError` and, on failure, set
`self.next_run = None` and return (leaving the parsed field lists empty). Keep
the existing wrong-field-count early return and all valid-expression behavior
unchanged. Add tests: `test_cron_zero_step_degrades` (`*/0` -> next_run None,
no raise) and `test_cron_non_numeric_field_degrades` (`abc` -> next_run None,
no raise).

Issue: #333
