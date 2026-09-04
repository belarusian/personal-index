# TICKET-366: content_health.ContentHealthChecker class docstring "indexed content" over-promise

Status: RESOLVED
Issue: #570
Module: personal_index/content_health.py
Class: (b) doc-drift (docstring over-promise)

## Symptom
The `ContentHealthChecker` class docstring (line 124) reads:
    "Checks health and quality of indexed content."
The phrase "indexed content" names a data SOURCE the code never touches.

## Evidence
- `__init__` (line 130) takes NO index/store handle; it only stores
  `self.config = config or ContentHealthCheck()`.
- Data is supplied manually via `check_item(url, title, content, tags, score,
  status_code)` (line 142) and `check_all(items: list[dict])` (line 286), which
  delegates to `_check_from_dict` -> `check_item`.
- There is no index object, no store, no crawler handle anywhere in the class.

## Minimal additive fix
Reword the `ContentHealthChecker` class docstring to state the exact mechanism
the body performs:
    "Checks health and quality of content items passed to check_item/check_all.

    Validates content items against configurable rules and
    generates health reports."
Add ONE behavior test pinning the corrected claim against the returned object:
a fresh `ContentHealthChecker()` holds no content (check_all([]) yields a report
with total_items == 0) and check_all surfaces exactly the items passed in
(report.total_items == len(items), report.results[i].url == items[i]["url"]).
This witnesses the "passed to check_item/check_all" claim, not just the reword.
