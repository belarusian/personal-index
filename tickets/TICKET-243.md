# TICKET-243: ruff gate RED on main - 37 lint errors

## File
Multiple (see evidence). Gate command `ruff check .` exits non-zero.

## Symptom
`ruff check .` reports 37 errors, so the local gate is RED on main.

## Evidence (measured, cycle 1)
- 22x E741 ambiguous `l` - tests/test_link.py (7), tests/test_linker.py (12), tests/test_scraper.py:56, tests/test_ticket97_docstrings.py:68,77
- 4x E402 module-level import not at top - personal_index/cli.py:1470-1472 (cli_dedup/cli_health/cli_recommend)
- 1x E401 multiple imports on one line - tests/test_archiver.py:103
- 8x F401 unused import - build_scheduler_subsystem.py:6 (textwrap), test_experiment.py:3 (pytest), tests/test_backup_store.py:3 (json),:4 (tempfile),:6 (BackupEntry), tests/test_rate_limit.py:3 (time), tests/test_router.py:4 (RouteMatcher), tests/test_health.py:6 (HealthStatus)
- 1x F811 redefinition of unused `tempfile` - tests/test_backup_store.py:66
- 1x F841 unused local `a2` - tests/test_alert.py:63

## Minimal additive fix
Rename `l`->`link`/`line`; move cli command imports to top (no circular import verified);
split the one-line import; drop genuinely unused imports; drop unused local; remove the
redundant in-function `import tempfile` (top-level import already present).

## Issue: #321 (gh)

## Status: RESOLVED (merged to main, cycle 1)
