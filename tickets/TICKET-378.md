# TICKET-378: format_schedule_job crashes on dict job with seed_urls=None

- Status: OPEN
- Issue: #594
- File: personal_index/formatter.py
- Function: format_schedule_job (line 73)
- Class: (a) behavioral

## Symptom
`format_schedule_job` accepts `dict[str, Any] | ScheduledJob`. When the dict
has the key `seed_urls` present but set to `None` (a common JSON shape, e.g.
`{"name": "x", "seed_urls": null}`), the function raises
`TypeError: can only join an iterable` at the `', '.join(seed_urls)` line.

## Evidence
Probe:
    format_schedule_job({'name':'x','seed_urls':None})
    -> TypeError: can only join an iterable
Root cause: `seed_urls = job.get('seed_urls', [])` — the `[]` default only
applies when the key is ABSENT, not when it is present-but-None. The
ScheduledJob dataclass branch is unaffected (field default_factory=list),
but the dict branch is a documented input type.

## Minimal additive fix
In the dict branch, coerce a None value to an empty list:
    seed_urls = job.get('seed_urls') or []
This preserves existing behavior for absent key (-> []) and for a real list,
and fixes the present-but-None case. No change to the ScheduledJob or
getattr fallback branches.

## Test
Add a behavior test that passes a dict job with `seed_urls=None` and asserts
the output renders "Seed URLs:" without raising. Fails pre-fix (TypeError),
passes post-fix.
