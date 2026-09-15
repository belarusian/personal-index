"""Adversarial deep tests for personal_index.content_api.

Contract source: module docstrings (personal_index/content_api.py).
This module has NO dedicated docs page, so the docstrings are the contract.

ContentAPI.handle_request(method, path, body, query_string) -> (status, payload)
is the public entry point; every route handler below is reached through it.

DEFECT (QA-31): _list_content negative per_page negative-slice leak.
The docstring says "per_page is capped at 100" (a bounded positive quantity)
and "items is the requested page slice of the store". But per_page is only
capped at the TOP (``per_page = min(per_page, 100)``) and never clamped at the
bottom. With a negative per_page, ``end = start + per_page`` becomes negative,
so ``items[start:end]`` performs a NEGATIVE SLICE (counts from the end) and
returns a PARTIAL list whose size depends on the magnitude of per_page:
per_page=-1 -> all-but-last item, per_page=-5 -> all-but-5, per_page=-10 -> [].
This is the "top N" negative-slice leak class (QA-1..QA-16) reached through the
public handle_request entry point. An out-of-range per_page should be clamped
to 0 (empty page, identical to per_page=0), not leak a partial page. Pinned
xfail-strict below.
"""

from __future__ import annotations

import json
import subprocess
import sys


from personal_index.content_api import ContentAPI, RequestLogger


def _seed(api: ContentAPI, n: int) -> None:
    """Seed the store with n items, ids '1'..'n'."""
    for i in range(1, n + 1):
        api._store[str(i)] = {
            "id": str(i),
            "title": f"Title {i}",
            "description": f"desc {i}",
            "link": f"http://x/{i}",
            "tags": [],
            "created_at": "",
            "updated_at": "",
        }


def _list(api: ContentAPI, qs: str = "") -> tuple[int, dict]:
    return api.handle_request("GET", "/api/v1/content", None, qs)


# ---------------------------------------------------------------------------
# Routing / 404 / health / stats
# ---------------------------------------------------------------------------


def test_unknown_path_returns_404():
    api = ContentAPI()
    status, payload = api.handle_request("GET", "/api/v9/nope")
    assert status == 404
    assert payload["error"] == "Not found"
    assert payload["path"] == "/api/v9/nope"


def test_health_check_returns_200_healthy():
    api = ContentAPI()
    status, payload = api.handle_request("GET", "/api/v1/health")
    assert status == 200
    assert payload["status"] == "healthy"
    assert "timestamp" in payload


def test_stats_empty_store():
    api = ContentAPI()
    status, payload = api.handle_request("GET", "/api/v1/stats")
    assert status == 200
    assert payload["total_items"] == 0
    assert payload["tags"] == {}


def test_stats_counts_tags_across_items():
    api = ContentAPI()
    api._store["1"] = {"id": "1", "title": "a", "description": "", "link": "", "tags": ["x", "y"], "created_at": "", "updated_at": ""}
    api._store["2"] = {"id": "2", "title": "b", "description": "", "link": "", "tags": ["x"], "created_at": "", "updated_at": ""}
    status, payload = api.handle_request("GET", "/api/v1/stats")
    assert status == 200
    assert payload["total_items"] == 2
    assert payload["tags"] == {"x": 2, "y": 1}


def test_put_to_collection_returns_404():
    # PUT is only valid on /content/{id}; on /content it maps to None -> 404.
    api = ContentAPI()
    status, _ = api.handle_request("PUT", "/api/v1/content", "{}")
    assert status == 404


def test_delete_to_collection_returns_404():
    api = ContentAPI()
    status, _ = api.handle_request("DELETE", "/api/v1/content")
    assert status == 404


def test_post_to_search_returns_404():
    # search/export are GET-only; POST maps to None -> 404.
    api = ContentAPI()
    status, _ = api.handle_request("POST", "/api/v1/content/search", "{}")
    assert status == 404


# ---------------------------------------------------------------------------
# List content / pagination
# ---------------------------------------------------------------------------


def test_list_empty_store():
    api = ContentAPI()
    status, payload = _list(api)
    assert status == 200
    assert payload["items"] == []
    assert payload["total"] == 0
    assert payload["page"] == 1
    assert payload["per_page"] == 20


def test_list_default_page_slice():
    api = ContentAPI()
    _seed(api, 5)
    status, payload = _list(api, "page=1&per_page=2")
    assert status == 200
    assert [it["id"] for it in payload["items"]] == ["1", "2"]
    assert payload["total"] == 5


def test_list_second_page():
    api = ContentAPI()
    _seed(api, 5)
    status, payload = _list(api, "page=2&per_page=2")
    assert status == 200
    assert [it["id"] for it in payload["items"]] == ["3", "4"]


def test_list_page_beyond_range_returns_empty_but_total_correct():
    api = ContentAPI()
    _seed(api, 3)
    status, payload = _list(api, "page=99&per_page=10")
    assert status == 200
    assert payload["items"] == []
    assert payload["total"] == 3


def test_list_per_page_capped_at_100():
    api = ContentAPI()
    _seed(api, 5)
    status, payload = _list(api, "per_page=1000")
    assert status == 200
    assert payload["per_page"] == 100
    assert len(payload["items"]) == 5


def test_list_non_integer_page_returns_400():
    api = ContentAPI()
    _seed(api, 3)
    status, payload = _list(api, "page=abc")
    assert status == 400
    assert "integers" in payload["error"]


def test_list_non_integer_per_page_returns_400():
    api = ContentAPI()
    _seed(api, 3)
    status, payload = _list(api, "per_page=xyz")
    assert status == 400
    assert "integers" in payload["error"]


def test_list_per_page_zero_returns_empty():
    api = ContentAPI()
    _seed(api, 3)
    status, payload = _list(api, "per_page=0")
    assert status == 200
    assert payload["items"] == []
    assert payload["total"] == 3


def test_list_negative_per_page_is_clamped_to_empty():
    api = ContentAPI()
    _seed(api, 10)
    status, payload = _list(api, "per_page=-1")
    assert status == 200
    # Out-of-range per_page must behave like per_page=0: an empty page.
    assert payload["items"] == []
    assert payload["total"] == 10


# ---------------------------------------------------------------------------
# Create content
# ---------------------------------------------------------------------------


def test_create_valid_body_returns_201():
    api = ContentAPI()
    status, payload = api.handle_request("POST", "/api/v1/content", json.dumps({"title": "T"}))
    assert status == 201
    assert payload["item"]["id"] == "1"
    assert payload["item"]["title"] == "T"


def test_create_missing_body_returns_400():
    api = ContentAPI()
    status, payload = api.handle_request("POST", "/api/v1/content", None)
    assert status == 400
    assert payload["error"] == "Request body is required"


def test_create_empty_body_returns_400():
    api = ContentAPI()
    status, payload = api.handle_request("POST", "/api/v1/content", "")
    assert status == 400
    assert payload["error"] == "Request body is required"


def test_create_invalid_json_returns_400():
    api = ContentAPI()
    status, payload = api.handle_request("POST", "/api/v1/content", "{not json")
    assert status == 400
    assert payload["error"] == "Invalid JSON in request body"


def test_create_non_object_array_returns_400():
    api = ContentAPI()
    status, payload = api.handle_request("POST", "/api/v1/content", "[1,2,3]")
    assert status == 400
    assert payload["error"] == "Request body must be a JSON object"


def test_create_non_object_scalar_returns_400():
    api = ContentAPI()
    status, payload = api.handle_request("POST", "/api/v1/content", "42")
    assert status == 400
    assert payload["error"] == "Request body must be a JSON object"


def test_create_applies_defaults():
    api = ContentAPI()
    status, payload = api.handle_request("POST", "/api/v1/content", "{}")
    assert status == 201
    item = payload["item"]
    assert item["title"] == "Untitled"
    assert item["description"] == ""
    assert item["link"] == ""
    assert item["tags"] == []


def test_create_ids_increment():
    api = ContentAPI()
    api.handle_request("POST", "/api/v1/content", "{}")
    status, payload = api.handle_request("POST", "/api/v1/content", "{}")
    assert status == 201
    assert payload["item"]["id"] == "2"


def test_create_unicode_title_round_trips():
    api = ContentAPI()
    body = json.dumps({"title": "Ünïcödé 标题 🚀"})
    status, payload = api.handle_request("POST", "/api/v1/content", body)
    assert status == 201
    assert payload["item"]["title"] == "Ünïcödé 标题 🚀"
    # round-trip through GET
    g_status, g_payload = api.handle_request("GET", "/api/v1/content/1")
    assert g_status == 200
    assert g_payload["item"]["title"] == "Ünïcödé 标题 🚀"


def test_create_duplicate_title_is_allowed():
    api = ContentAPI()
    api.handle_request("POST", "/api/v1/content", json.dumps({"title": "same"}))
    status, _ = api.handle_request("POST", "/api/v1/content", json.dumps({"title": "same"}))
    assert status == 201  # no uniqueness constraint


# ---------------------------------------------------------------------------
# Get content
# ---------------------------------------------------------------------------


def test_get_existing_returns_200():
    api = ContentAPI()
    _seed(api, 1)
    status, payload = api.handle_request("GET", "/api/v1/content/1")
    assert status == 200
    assert payload["item"]["id"] == "1"


def test_get_missing_returns_404():
    api = ContentAPI()
    status, payload = api.handle_request("GET", "/api/v1/content/999")
    assert status == 404
    assert "not found" in payload["error"]


def test_get_whitespace_id_returns_404():
    api = ContentAPI()
    _seed(api, 1)
    # a whitespace-only id is a distinct key -> not found
    status, _ = api.handle_request("GET", "/api/v1/content/%20%20")
    assert status == 404


# ---------------------------------------------------------------------------
# Update content
# ---------------------------------------------------------------------------


def test_update_existing_changes_field():
    api = ContentAPI()
    _seed(api, 1)
    status, payload = api.handle_request("PUT", "/api/v1/content/1", json.dumps({"title": "NEW"}))
    assert status == 200
    assert payload["item"]["title"] == "NEW"


def test_update_missing_returns_404():
    api = ContentAPI()
    status, payload = api.handle_request("PUT", "/api/v1/content/999", json.dumps({"title": "x"}))
    assert status == 404
    assert "not found" in payload["error"]


def test_update_missing_body_returns_400():
    api = ContentAPI()
    _seed(api, 1)
    status, payload = api.handle_request("PUT", "/api/v1/content/1", None)
    assert status == 400
    assert payload["error"] == "Request body is required"


def test_update_invalid_json_returns_400():
    api = ContentAPI()
    _seed(api, 1)
    status, payload = api.handle_request("PUT", "/api/v1/content/1", "{bad")
    assert status == 400
    assert payload["error"] == "Invalid JSON in request body"


def test_update_non_object_returns_400():
    api = ContentAPI()
    _seed(api, 1)
    status, payload = api.handle_request("PUT", "/api/v1/content/1", "null")
    assert status == 400
    assert payload["error"] == "Request body must be a JSON object"


def test_update_partial_preserves_other_fields():
    api = ContentAPI()
    _seed(api, 1)
    status, payload = api.handle_request("PUT", "/api/v1/content/1", json.dumps({"title": "NEW"}))
    assert status == 200
    item = payload["item"]
    assert item["title"] == "NEW"
    assert item["description"] == "desc 1"  # untouched
    assert item["link"] == "http://x/1"  # untouched


def test_update_is_idempotent():
    api = ContentAPI()
    _seed(api, 1)
    body = json.dumps({"title": "SAME"})
    s1, p1 = api.handle_request("PUT", "/api/v1/content/1", body)
    s2, p2 = api.handle_request("PUT", "/api/v1/content/1", body)
    assert s1 == s2 == 200
    assert p1["item"]["title"] == p2["item"]["title"] == "SAME"


def test_update_refreshes_updated_at():
    api = ContentAPI()
    _seed(api, 1)
    before = api._store["1"]["updated_at"]
    api.handle_request("PUT", "/api/v1/content/1", json.dumps({"title": "x"}))
    after = api._store["1"]["updated_at"]
    assert after != before  # now(UTC).isoformat() advances


# ---------------------------------------------------------------------------
# Delete content
# ---------------------------------------------------------------------------


def test_delete_existing_returns_200():
    api = ContentAPI()
    _seed(api, 1)
    status, payload = api.handle_request("DELETE", "/api/v1/content/1")
    assert status == 200
    assert payload["deleted"] is True
    assert payload["id"] == "1"


def test_delete_missing_returns_404():
    api = ContentAPI()
    status, payload = api.handle_request("DELETE", "/api/v1/content/999")
    assert status == 404
    assert "not found" in payload["error"]


def test_delete_is_not_idempotent_second_call_404():
    api = ContentAPI()
    _seed(api, 1)
    s1, _ = api.handle_request("DELETE", "/api/v1/content/1")
    s2, _ = api.handle_request("DELETE", "/api/v1/content/1")
    assert s1 == 200
    assert s2 == 404


def test_delete_then_get_returns_404():
    api = ContentAPI()
    _seed(api, 1)
    api.handle_request("DELETE", "/api/v1/content/1")
    status, _ = api.handle_request("GET", "/api/v1/content/1")
    assert status == 404


# ---------------------------------------------------------------------------
# Search content
# ---------------------------------------------------------------------------


def test_search_empty_query_returns_400():
    api = ContentAPI()
    _seed(api, 1)
    status, payload = api.handle_request("GET", "/api/v1/content/search", None, "q=")
    assert status == 400
    assert "required" in payload["error"]


def test_search_missing_query_returns_400():
    api = ContentAPI()
    _seed(api, 1)
    status, payload = api.handle_request("GET", "/api/v1/content/search", None, "")
    assert status == 400
    assert "required" in payload["error"]


def test_search_case_insensitive_substring():
    api = ContentAPI()
    _seed(api, 3)
    status, payload = api.handle_request("GET", "/api/v1/content/search", None, "q=TITLE")
    assert status == 200
    assert payload["total"] == 3  # every title contains 'title'
    assert payload["query"] == "TITLE"


def test_search_no_match_returns_empty():
    api = ContentAPI()
    _seed(api, 3)
    status, payload = api.handle_request("GET", "/api/v1/content/search", None, "q=zzzz")
    assert status == 200
    assert payload["results"] == []
    assert payload["total"] == 0


def test_search_unicode_query():
    api = ContentAPI()
    api._store["1"] = {"id": "1", "title": "café", "description": "", "link": "", "tags": [], "created_at": "", "updated_at": ""}
    status, payload = api.handle_request("GET", "/api/v1/content/search", None, "q=caf%C3%A9")
    assert status == 200
    assert payload["total"] == 1


# ---------------------------------------------------------------------------
# Export content
# ---------------------------------------------------------------------------


def test_export_default_json():
    api = ContentAPI()
    _seed(api, 2)
    status, payload = api.handle_request("GET", "/api/v1/content/export", None, "")
    assert status == 200
    assert payload["format"] == "json"
    assert payload["total"] == 2
    assert len(payload["items"]) == 2


def test_export_custom_format():
    api = ContentAPI()
    _seed(api, 1)
    status, payload = api.handle_request("GET", "/api/v1/content/export", None, "format=csv")
    assert status == 200
    assert payload["format"] == "csv"


def test_export_empty_store():
    api = ContentAPI()
    status, payload = api.handle_request("GET", "/api/v1/content/export", None, "")
    assert status == 200
    assert payload["items"] == []
    assert payload["total"] == 0


# ---------------------------------------------------------------------------
# RequestLogger middleware
# ---------------------------------------------------------------------------


def test_request_logger_records_status():
    api = ContentAPI()
    logger = RequestLogger(api)
    logger.handle_request("GET", "/api/v1/health")
    logger.handle_request("GET", "/api/v1/nope")
    log = logger.log
    assert len(log) == 2
    assert log[0]["status"] == 200
    assert log[1]["status"] == 404
    assert log[0]["method"] == "GET"
    assert log[0]["path"] == "/api/v1/health"


def test_request_logger_clear():
    api = ContentAPI()
    logger = RequestLogger(api)
    logger.handle_request("GET", "/api/v1/health")
    logger.clear_log()
    assert logger.log == []


# ---------------------------------------------------------------------------
# End-to-end CLI run (content_api is not wired to a subcommand, so exercise
# the installed CLI entry point directly).
# ---------------------------------------------------------------------------


def test_cli_status_runs_end_to_end():
    proc = subprocess.run(
        [sys.executable, "-m", "personal_index", "status"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0
    assert "Personal Index Status" in proc.stdout


# ---------------------------------------------------------------------------
# ARCH-68: _validate_content wired into the POST/PUT request path
#
# Contract (tickets/ARCH-68.md + module docstrings): after the inline
# isinstance(data, dict) guard, a non-empty _validate_content(data) error
# list maps to (400, {"error": <first error>}) BEFORE the item is
# stored/updated. Field rules: title (if present) must be a str of length
# <= 200; tags (if present) must be a list. The existing body guards
# (missing/empty body, invalid JSON, non-dict body) still take precedence.
# ---------------------------------------------------------------------------


def _post(api: ContentAPI, body: str) -> tuple[int, dict]:
    return api.handle_request("POST", "/api/v1/content", body)


def _put(api: ContentAPI, item_id: str, body: str) -> tuple[int, dict]:
    return api.handle_request("PUT", f"/api/v1/content/{item_id}", body)


def _seed_one(api: ContentAPI) -> str:
    status, payload = _post(api, json.dumps({"title": "Seed", "tags": ["a"]}))
    assert status == 201
    return str(payload["item"]["id"])


# --- Acceptance criteria (pinning, through the public handle_request) ---


def test_arch68_create_overlong_title_400_store_unchanged():
    api = ContentAPI()
    status, payload = _post(api, json.dumps({"title": "x" * 201}))
    assert status == 400
    assert payload["error"] == "Title must be under 200 characters"
    assert len(api._store) == 0
    assert api._next_id == 1


def test_arch68_create_nonlist_tags_400_store_unchanged():
    api = ContentAPI()
    status, payload = _post(api, json.dumps({"tags": "not-a-list"}))
    assert status == 400
    assert payload["error"] == "Tags must be a list"
    assert len(api._store) == 0
    assert api._next_id == 1


def test_arch68_update_overlong_title_400_item_unchanged():
    api = ContentAPI()
    item_id = _seed_one(api)
    before_title = api._store[item_id]["title"]
    before_updated = api._store[item_id]["updated_at"]
    status, payload = _put(api, item_id, json.dumps({"title": "x" * 201}))
    assert status == 400
    assert payload["error"] == "Title must be under 200 characters"
    assert api._store[item_id]["title"] == before_title
    assert api._store[item_id]["updated_at"] == before_updated


def test_arch68_create_valid_body_201_stored():
    api = ContentAPI()
    status, payload = _post(api, json.dumps({"title": "ok", "tags": ["a"]}))
    assert status == 201
    assert payload["item"]["title"] == "ok"
    assert payload["item"]["tags"] == ["a"]
    assert len(api._store) == 1


def test_arch68_create_non_dict_400_isinstance_first():
    api = ContentAPI()
    status, payload = _post(api, "[1, 2]")
    assert status == 400
    assert payload["error"] == "Request body must be a JSON object"
    assert len(api._store) == 0


# --- Adversarial: title length boundary (contract is <= 200) ---


def test_arch68_title_exactly_200_accepted():
    api = ContentAPI()
    status, payload = _post(api, json.dumps({"title": "x" * 200}))
    assert status == 201
    assert payload["item"]["title"] == "x" * 200


def test_arch68_title_201_rejected():
    api = ContentAPI()
    status, payload = _post(api, json.dumps({"title": "x" * 201}))
    assert status == 400
    assert payload["error"] == "Title must be under 200 characters"


def test_arch68_title_202_rejected():
    api = ContentAPI()
    status, payload = _post(api, json.dumps({"title": "x" * 202}))
    assert status == 400
    assert payload["error"] == "Title must be under 200 characters"


def test_arch68_empty_string_title_accepted():
    api = ContentAPI()
    status, payload = _post(api, json.dumps({"title": ""}))
    assert status == 201
    assert payload["item"]["title"] == ""


# --- Adversarial: title type guard (must be a str) ---


def test_arch68_title_int_rejected():
    api = ContentAPI()
    status, payload = _post(api, json.dumps({"title": 123}))
    assert status == 400
    assert payload["error"] == "Title must be a string"
    assert len(api._store) == 0


def test_arch68_title_none_rejected():
    api = ContentAPI()
    status, payload = _post(api, json.dumps({"title": None}))
    assert status == 400
    assert payload["error"] == "Title must be a string"
    assert len(api._store) == 0


def test_arch68_title_list_rejected():
    api = ContentAPI()
    status, payload = _post(api, json.dumps({"title": ["a", "b"]}))
    assert status == 400
    assert payload["error"] == "Title must be a string"
    assert len(api._store) == 0


def test_arch68_title_dict_rejected():
    api = ContentAPI()
    status, payload = _post(api, json.dumps({"title": {"k": "v"}}))
    assert status == 400
    assert payload["error"] == "Title must be a string"
    assert len(api._store) == 0


# --- Adversarial: tags type guard (must be a list) ---


def test_arch68_tags_int_rejected():
    api = ContentAPI()
    status, payload = _post(api, json.dumps({"tags": 5}))
    assert status == 400
    assert payload["error"] == "Tags must be a list"
    assert len(api._store) == 0


def test_arch68_tags_none_rejected():
    api = ContentAPI()
    status, payload = _post(api, json.dumps({"tags": None}))
    assert status == 400
    assert payload["error"] == "Tags must be a list"
    assert len(api._store) == 0


def test_arch68_tags_dict_rejected():
    api = ContentAPI()
    status, payload = _post(api, json.dumps({"tags": {"a": 1}}))
    assert status == 400
    assert payload["error"] == "Tags must be a list"
    assert len(api._store) == 0


def test_arch68_tags_empty_list_accepted():
    api = ContentAPI()
    status, payload = _post(api, json.dumps({"title": "T", "tags": []}))
    assert status == 201
    assert payload["item"]["tags"] == []


def test_arch68_tags_list_accepted():
    api = ContentAPI()
    status, payload = _post(api, json.dumps({"title": "T", "tags": ["a", "b"]}))
    assert status == 201
    assert payload["item"]["tags"] == ["a", "b"]


# --- Adversarial: PUT path field validation ---


def test_arch68_update_nonlist_tags_400_item_unchanged():
    api = ContentAPI()
    item_id = _seed_one(api)
    before_tags = api._store[item_id]["tags"]
    before_updated = api._store[item_id]["updated_at"]
    status, payload = _put(api, item_id, json.dumps({"tags": "nope"}))
    assert status == 400
    assert payload["error"] == "Tags must be a list"
    assert api._store[item_id]["tags"] == before_tags
    assert api._store[item_id]["updated_at"] == before_updated


def test_arch68_update_non_string_title_400_item_unchanged():
    api = ContentAPI()
    item_id = _seed_one(api)
    before_title = api._store[item_id]["title"]
    before_updated = api._store[item_id]["updated_at"]
    status, payload = _put(api, item_id, json.dumps({"title": 999}))
    assert status == 400
    assert payload["error"] == "Title must be a string"
    assert api._store[item_id]["title"] == before_title
    assert api._store[item_id]["updated_at"] == before_updated


def test_arch68_update_valid_body_still_200():
    api = ContentAPI()
    item_id = _seed_one(api)
    status, payload = _put(api, item_id, json.dumps({"title": "New", "tags": ["z"]}))
    assert status == 200
    assert payload["item"]["title"] == "New"
    assert payload["item"]["tags"] == ["z"]


# --- Adversarial: first-error-wins + precedence + idempotence ---


def test_arch68_first_error_wins_title_before_tags():
    api = ContentAPI()
    status, payload = _post(api, json.dumps({"title": "x" * 201, "tags": "bad"}))
    assert status == 400
    # title is checked before tags, so the title error is errors[0].
    assert payload["error"] == "Title must be under 200 characters"
    assert len(api._store) == 0


def test_arch68_repeated_rejections_keep_store_empty():
    api = ContentAPI()
    for _ in range(3):
        status, _ = _post(api, json.dumps({"title": "x" * 201}))
        assert status == 400
    assert len(api._store) == 0
    assert api._next_id == 1


def test_arch68_empty_dict_body_accepted():
    api = ContentAPI()
    status, payload = _post(api, "{}")
    assert status == 201
    assert payload["item"]["title"] == "Untitled"
    assert payload["item"]["tags"] == []


def test_arch68_unicode_title_overlong_rejected():
    api = ContentAPI()
    status, payload = _post(api, json.dumps({"title": "\u0441" * 201}))
    assert status == 400
    assert payload["error"] == "Title must be under 200 characters"
    assert len(api._store) == 0


def test_arch68_unicode_title_underlong_accepted():
    api = ContentAPI()
    status, payload = _post(api, json.dumps({"title": "\u0441" * 200}))
    assert status == 201
    assert payload["item"]["title"] == "\u0441" * 200
