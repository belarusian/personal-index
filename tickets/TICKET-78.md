# TICKET-78: Use ternary operator instead of if-else block (SIM108)

## Title
Multiple assignments use `if`-`else` blocks that can be replaced with ternary expressions

## Evidence
ruff SIM108 flags 5 locations:

1. `personal_index/analytics.py:255` — domain extraction
2. `personal_index/export_markdown.py:291` — items assignment
3. `personal_index/export_markdown.py:315` — items assignment (duplicate pattern)
4. `personal_index/url_utils.py:342` — urljoin conditional

Example pattern:
