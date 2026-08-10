# TICKET-64: f-strings without placeholders (F541)

## Title
f-string prefix used on strings with no interpolation — unnecessary overhead and misleading

## Evidence
ruff F541 flags 2 locations in `personal_index/cli.py`:

1. `personal_index/cli.py:207` — `f"\nCrawler:"` has no `{}` placeholders
2. `personal_index/cli.py:213` — `f"\nSchedule:"` has no `{}` placeholders
