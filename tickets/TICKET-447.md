# TICKET-447: content_health.ContentHealthChecker.check_item docstring order claim not delivered by code

## File
personal_index/content_health.py

## Symptom
The `check_item` docstring (introduced by the parallel pipeline's TICKET-444
reword, commit 1c3024f) claims the seven checks run "in order" and enumerates
them:

    1. url
    2. title presence
    3. title length
    4. content length
    5. status code
    6. tags
    7. score

But the actual dispatch order in `_check_item_funcs` (lines 185-193) is:

    1. _check_url
    2. _check_title_presence
    3. _check_title_length
    4. _check_content_length
    5. _check_tags
    6. _check_score
    7. _check_status_code

So the docstring promises `bad_status` (status code) is produced as the 5th
issue, but the body produces it as the 7th (last). The order of the
`issues` list in the returned `HealthCheckResult` is a real, observable,
testable behavior, and the code does not deliver the documented order.

## Evidence
- Docstring order claim: personal_index/content_health.py lines 144-162
  ("Runs up to seven checks in order ... 5. status code ... 6. tags ... 7. score")
- Code dispatch order: personal_index/content_health.py lines 185-193
  (`_check_item_funcs` = [url, title_presence, title_length, content_length,
   tags, score, status_code])

## Minimal additive fix
Reorder `_check_item_funcs` so the dispatch order matches the documented
order: [url, title_presence, title_length, content_length, status_code,
tags, score]. This makes the ORIGINAL/current docstring order claim true
without touching the docstring. Add a pinning test asserting the issue
order for a fully-failing item.

## Classification
IMPLEMENTABLE (the documented order is achievable by reordering the
dispatch list; no contract conflict).

Issue: #731

## Status
OPEN
