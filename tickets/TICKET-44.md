# TICKET-44: Builtin shadowing — `content_export_csv.py:46` and `export_markdown.py:57` use `format` as parameter name

## Title
Parameter named `format` shadows Python builtin `format()`

## Evidence
In `personal_index/content_export_csv.py:46`:
