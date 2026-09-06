# TICKET-486: content_priority.calculate accepts unused tags parameter

## File
personal_index/content_priority.py

## Symptom
The `PriorityCalculator.calculate()` method signature accepts a `tags: list[str] | None = None` parameter, and the `batch_calculate()` docstring documents `tags` as a valid item key, but the parameter is never used in the scoring logic. The tags are silently ignored, making the API misleading.

## Evidence
Line 98: `tags: list[str] | None = None,` in calculate signature
Line 201: docstring mentions `tags` as a key in batch_calculate items
Line 215: `tags=item.get("tags", [])` is passed to calculate but never used
The calculate method body (lines 110-145) never references `tags`

## Minimal Additive Fix
Remove the unused `tags` parameter from `calculate()` signature and from `batch_calculate()` docstring and call site, or alternatively implement tag-based scoring. Removing the unused parameter is the minimal fix that eliminates the misleading API.

## Issue
Issue: #825 (CLOSED)
