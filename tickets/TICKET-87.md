# TICKET-87: Type error — `restore_backup()` return dict has `str` values where `int` expected

## Title
`restore_backup()` return dict mixes `str` and `int` values, conflicting with inferred dict type

## Evidence
File: `personal_index/backup.py`
Lines 163-168:
