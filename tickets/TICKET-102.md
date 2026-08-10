# TICKET-102: BLE001 — Blind exception handling in crawler modules

## Title
Crawler modules use `except Exception:` which can hide critical errors

## Evidence
Files:
- `personal_index/crawler/__init__.py` line 114
- `personal_index/crawler/main.py` line 138

Both files catch `Exception:` which will hide system-level errors like `KeyboardInterrupt`, `SystemExit`, and memory errors.

Example from `crawler/__init__.py`:
