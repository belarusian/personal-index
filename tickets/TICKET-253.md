# TICKET-253: CLI `schedule run` does not persist run state back to the store

Status: OPEN
Module: personal_index/cli.py
Symptom: `schedule run <name>` (cli.py `schedule_run`, line 1178) executes the
crawl pipeline and prints the page count, but never writes the run back to the
schedule store. After a manual run, `run_count`, `last_run`, `next_run` and
`total_pages_indexed` are all unchanged on disk. This contradicts the module's
own `Scheduler.run_schedule` (scheduler.py:220), which increments `run_count`,
sets `last_run`, advances `next_run` by `interval_hours`, and calls
`store.update(entry)`. A user who runs a job manually gets no record that it
ran and the next scheduled time is never advanced.

Evidence (verified on main):
- `schedule_run` (cli.py:1178-1200): after `stats = runner.run(...)` it only
  does `click.echo(...)`; `grep -c 'store.update\|run_count\|last_run'` over
  lines 1178-1200 == 0. No `ScheduleStore` is even opened in the run path.
- Contrast `Scheduler.run_schedule` (scheduler.py:220-249): sets
  `entry.run_count += 1`, `entry.total_pages_indexed += len(pages)`,
  `entry.last_run = datetime.now(timezone.utc)`,
  `entry.next_run = entry.last_run + timedelta(hours=interval)`,
  `self.schedule_store.update(entry)`.
- `runner.run()` returns `PipelineStats` (pipeline_runner.py:286) with
  `pages_crawled: int`, so the page count is available to persist.

Fix (minimal, additive): in `schedule_run`, after a successful `runner.run`,
open the `ScheduleStore` at `store_path`, update the entry's
`run_count += 1`, `total_pages_indexed += stats.pages_crawled`,
`last_run = datetime.now(timezone.utc)`,
`next_run = last_run + timedelta(hours=entry.config.interval_hours)`, and call
`store.update(entry)`. Do this only on the success path (not in `except`), and
before/inside the `finally` that closes the runner. Add a test that runs a job
and asserts the store file now records `run_count == 1`, a non-null `last_run`,
and an advanced `next_run`.

Issue: #335
