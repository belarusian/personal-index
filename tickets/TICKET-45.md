# TICKET-45: Broad exception handling — multiple modules catch `Exception` and silently return

## Title
Multiple functions catch `Exception` broadly and return silently, swallowing errors

## Evidence
Found in the following locations:

1. `personal_index/url_utils.py:36` — `extract_domain()` catches `Exception` and returns empty string
2. `personal_index/url_utils.py:99` — `normalize_url()` catches `Exception` and returns original URL
3. `personal_index/url_utils.py:139` — `extract_path()` catches `Exception` and returns empty string
4. `personal_index/url_utils.py:195` — `is_same_domain()` catches `Exception` and returns False
5. `personal_index/url_utils.py:230` — `remove_query_params()` catches `Exception` and returns None
6. `personal_index/url_utils.py:349` — `extract_links()` catches `Exception` and passes (returns empty list)
7. `personal_index/content_health.py:264` — catches `Exception` and returns
8. `personal_index/content_health.py:458` — catches `Exception` and returns
9. `personal_index/content_health.py:522` — catches `Exception` and returns
10. `personal_index/export_markdown.py:324` — catches `Exception` and returns

Example from `url_utils.py:34-38`:
