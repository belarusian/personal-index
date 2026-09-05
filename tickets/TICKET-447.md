# TICKET-447: content_health.check_item check-order not delivered by code

Status: OPEN
Issue: #731
Module: personal_index/content_health.py
Method: ContentHealthChecker.check_item / _check_item_funcs

## Symptom
The `check_item` docstring documents the seven checks running in order
[1 url, 2 title_presence, 3 title_length, 4 content_length,
5 status_code, 6 tags, 7 score]. But the `_check_item_funcs` dispatch
list runs [1 url, 2 title_presence, 3 title_length, 4 content_length,
5 tags, 6 score, 7 status_code]. The `issues` list order is observable
output, so the code does not deliver the documented order.

## Evidence
personal_index/content_health.py:
- docstring lines ~156-162: "5. status code ... 6. tags ... 7. score"
- _check_item_funcs lines ~185-193 dispatch order:
  _check_url, _check_title_presence, _check_title_length,
  _check_content_length, _check_tags, _check_score, _check_status_code

## Minimal additive fix
Reorder `_check_item_funcs` so the dispatch matches the documented order:
... _check_content_length, _check_status_code, _check_tags, _check_score.
The seven check functions are independent (each appends to issues and
returns ct/cp), so reordering is safe. Add ONE pinning test asserting the
RETURNED issues list order for an item that fails all seven checks.
No other behavior change.
