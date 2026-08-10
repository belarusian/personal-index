# TICKET-39: Return type mismatch — `url_utils.py:231` returns `None` but annotated as `-> str`

## Title
`remove_query_params()` returns `None` on exception but type annotation declares `-> str`

## Evidence
In `personal_index/url_utils.py:214-231`:
