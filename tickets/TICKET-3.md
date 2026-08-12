# TICKET-3: cli.py is 1398 lines — should be split into smaller modules

## Evidence

`personal_index/cli.py` is 1398 lines containing:
- `init` command (lines 78-126)
- `interests` group with add/list/remove (lines 127-196)
- `tags` group with add/list/remove (lines 197-259)
- `import` command (lines 260-320)
- `search` command (lines 345-415)
- `export` command (lines 429-522)
- `status` command (lines 523-575)
- `crawl` command (lines 576-624)
- `pipeline` command (lines 625-727)
- `stats` command (lines 728-793)
- `list` command (lines 794-851)
- `top` command (lines 852-875)
- `remove` command (lines 876-898)
- `clear` command (lines 899-926)
- `doctor` command (lines 927-986)
- `schedule` group with add/list/remove/run (lines 987-1100+)
- `watch` command (lines 1100+)

This violates the Single Responsibility Principle and makes the file extremely hard to navigate.

## Impact

- Difficult to review changes (any CLI change touches a 1398-line file)
- Hard to find specific command implementations
- Merge conflicts are more likely when multiple developers work on CLI
- Testing individual commands requires loading the entire file

## Suggestion

Split `cli.py` into separate command modules (one per command/group), following the pattern already started with `cli_dedup.py`, `cli_health.py`, and `cli_recommend.py`. Each module should define its command and export it for registration in a thin `cli.py` entry point.
