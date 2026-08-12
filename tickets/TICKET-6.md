# TICKET-6: 21 modules have no test coverage

## Evidence

The following modules have no corresponding `test_<module>.py` file:

1. `cli_clear.py` — clear command
2. `cli_doctor.py` — doctor command
3. `cli_extract.py` — extract command
4. `cli_import.py` — import command
5. `cli_interests.py` — interests CLI
6. `cli_list.py` — list command
7. `cli_merge.py` — merge command
8. `cli_pipeline.py` — pipeline CLI
9. `cli_pipeline_unified.py` — unified pipeline CLI
10. `cli_remove.py` — remove command
11. `cli_schedule.py` — schedule CLI
12. `cli_score.py` — score command
13. `cli_stats.py` — stats command
14. `cli_status.py` — status command
15. `cli_tags.py` — tags CLI
16. `cli_top.py` — top command
17. `cli_verify.py` — verify command
18. `cli_watch.py` — watch command
19. `content_timeline.py` — timeline functionality
20. `health.py` — health wrapper
21. `pipeline_runner.py` — pipeline runner

Note: Many of the CLI modules above (1-18) are dead code (see TICKET-1), so tests for them may not be needed if the modules are removed.

## Impact

- `pipeline_runner.py` and `content_timeline.py` are non-CLI modules with no tests — these are higher priority
- `health.py` has no tests despite being a health-check module
- If dead CLI modules are removed, test effort is saved

## Suggestion

1. **Priority 1:** Write tests for `pipeline_runner.py` and `content_timeline.py` — these are active modules with no coverage.
2. **Priority 2:** Write tests for `health.py`.
3. **Priority 3:** If dead CLI modules (1-18) are removed per TICKET-1, no tests needed. If they are wired up instead, write tests for each.
