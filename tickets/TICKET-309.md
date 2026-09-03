# TICKET-309: content_api._list_content unguarded int() on query params escapes as traceback

- Status: OPEN
- Module: personal_index/content_api.py
- Symptom: GET /api/v1/content?page=abc (or per_page=xyz) raises a raw
  ValueError: invalid literal for int() with base 10: 'abc' out of
  handle_request -> uncaught traceback / 500, instead of a clean 400.
- Evidence: content_api.py:80-81
    page = int(params.get("page", ["1"])[0])
    per_page = int(params.get("per_page", ["20"])[0])
  handle_request (line 33: result = handler()) has no try/except wrapper.
  Verified empirically: ContentAPI().handle_request("GET", "/api/v1/content",
  query_string="page=abc") -> ESCAPES AS: ValueError invalid literal for
  int() with base 10: 'abc'.
- Contract asymmetry: the SAME module guards the request-body contract in
  _create_content (line 106) and _update_content (line 131) with clean
  400 {"error": ...} responses, but the query-param contract in
  _list_content is unguarded. A client that sends a non-numeric page or
  per_page gets a traceback instead of a 400.
- Minimal additive fix: wrap the two int(...) conversions in a try/except
  ValueError in _list_content and return
  400, {"error": "Query parameters 'page' and 'per_page' must be integers"}
  on failure. Add tests test_list_page_non_numeric and
  test_list_per_page_non_numeric asserting a clean 400 (no exception).
- Issue: #453
