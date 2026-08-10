# TICKET-60: Deprecated typing imports — 503 instances of typing.List/Dict/Tuple should use builtins

## Title
503 instances of deprecated `typing.List`, `typing.Dict`, `typing.Tuple` should use `list`, `dict`, `tuple`

## Evidence
ruff UP035/UP006 reports 503 violations across the codebase. Example:

`personal_index/analytics.py:10`:
