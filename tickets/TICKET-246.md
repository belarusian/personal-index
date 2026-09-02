# TICKET-246: content_timeline/timeline.py - inline imports (import hygiene)

## File
personal_index/content_timeline/timeline.py

## Symptom
`get_events_for_week` and `get_events_for_month` use inline imports instead of
top-level module imports: `__import__("datetime").timedelta(...)` (lines 97, 100)
and `import calendar` (line 106). This is non-idiomatic, hides dependencies, and
defeats static analysis / import caching.

## Evidence (measured, cycle 2)
- Line 5: `from datetime import date, datetime, timezone` (timedelta NOT imported)
- Line 97: `monday = d - __import__("datetime").timedelta(days=d.weekday())`
- Line 100: `sunday = monday + __import__("datetime").timedelta(days=6)`
- Line 106: `import calendar` (inside get_events_for_month)

## Minimal additive fix
Add `timedelta` to the top-level datetime import (line 5) and add `import calendar`
at module top; replace the two `__import__("datetime").timedelta` calls with
`timedelta` and remove the inline `import calendar`. Behavior unchanged.

## Issue: #324 (gh)

## Status: OPEN
