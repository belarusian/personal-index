"""Tests for content_api module."""

import json

import pytest

import personal_index.content_api as api_module
from personal_index.content_api import ContentAPI


@pytest.fixture
def api():
    return ContentAPI()


@pytest.fixture
def api_with_data():
    api = ContentAPI()
    api._store = {
        "1": {"id": "1", "title": "First", "description": "Desc 1", "tags": ["a"]},
        "2": {"id": "2", "title": "Second", "description": "Desc 2", "tags": ["b"]},
    }
    return api


# --- Health & Stats ---

class TestHealthStats:
    def test_health_check(self, api):
        status, body = api.handle_request("GET", "/api/v1/health")
        assert status == 200
        assert body["status"] == "healthy"

    def test_stats(self, api_with_data):
        status, body = api_with_data.handle_request("GET", "/api/v1/stats")
        assert status == 200
        assert body["total_items"] == 2


# --- List Content ---

class TestListContent:
    def test_list_all(self, api_with_data):
        status, body = api_with_data.handle_request("GET", "/api/v1/content")
        assert status == 200
        assert body["total"] == 2
        assert len(body["items"]) == 2

    def test_list_empty(self, api):
        status, body = api.handle_request("GET", "/api/v1/content")
        assert status == 200
        assert body["total"] == 0

    def test_list_pagination(self, api_with_data):
        status, body = api_with_data.handle_request(
            "GET", "/api/v1/content", query_string="page=1&per_page=1"
        )
        assert status == 200
        assert len(body["items"]) == 1
        assert body["page"] == 1

    def test_list_per_page_max(self, api_with_data):
        _status, body = api_with_data.handle_request(
            "GET", "/api/v1/content", query_string="per_page=999"
        )
        assert body["per_page"] == 100

    def test_list_page_non_numeric(self, api_with_data):
        status, body = api_with_data.handle_request(
            "GET", "/api/v1/content", query_string="page=abc"
        )
        assert status == 400
        assert "error" in body

    def test_list_per_page_non_numeric(self, api_with_data):
        status, body = api_with_data.handle_request(
            "GET", "/api/v1/content", query_string="per_page=xyz"
        )
        assert status == 400
        assert "error" in body


# --- Create Content ---

class TestCreateContent:
    def test_create_basic(self, api):
        body = json.dumps({"title": "New Post", "description": "A new post"})
        status, resp = api.handle_request("POST", "/api/v1/content", body=body)
        assert status == 201
        assert resp["item"]["title"] == "New Post"
        assert "id" in resp["item"]

    def test_create_no_body(self, api):
        status, resp = api.handle_request("POST", "/api/v1/content")
        assert status == 400
        assert "required" in resp["error"]

    def test_create_invalid_json(self, api):
        status, _resp = api.handle_request("POST", "/api/v1/content", body="not json")
        assert status == 400

    def test_create_not_dict(self, api):
        status, _resp = api.handle_request("POST", "/api/v1/content", body='["list"]')
        assert status == 400

    def test_create_with_tags(self, api):
        body = json.dumps({"title": "T", "tags": ["x", "y"]})
        _status, resp = api.handle_request("POST", "/api/v1/content", body=body)
        assert resp["item"]["tags"] == ["x", "y"]

    def test_create_increments_id(self, api):
        body = json.dumps({"title": "A"})
        api.handle_request("POST", "/api/v1/content", body=body)
        api.handle_request("POST", "/api/v1/content", body=body)
        assert len(api._store) == 2


# --- Get Content ---

class TestGetContent:
    def test_get_existing(self, api_with_data):
        status, body = api_with_data.handle_request("GET", "/api/v1/content/1")
        assert status == 200
        assert body["item"]["title"] == "First"

    def test_get_not_found(self, api):
        status, _body = api.handle_request("GET", "/api/v1/content/999")
        assert status == 404


# --- Update Content ---

class TestUpdateContent:
    def test_update_existing(self, api_with_data):
        body = json.dumps({"title": "Updated"})
        status, resp = api_with_data.handle_request("PUT", "/api/v1/content/1", body=body)
        assert status == 200
        assert resp["item"]["title"] == "Updated"

    def test_update_not_found(self, api):
        status, _resp = api.handle_request("PUT", "/api/v1/content/999", body='{}')
        assert status == 404

    def test_update_no_body(self, api_with_data):
        status, _resp = api_with_data.handle_request("PUT", "/api/v1/content/1")
        assert status == 400

    def test_update_preserves_other_fields(self, api_with_data):
        body = json.dumps({"title": "New Title"})
        _status, resp = api_with_data.handle_request("PUT", "/api/v1/content/1", body=body)
        assert resp["item"]["description"] == "Desc 1"


# --- Delete Content ---

class TestDeleteContent:
    def test_delete_existing(self, api_with_data):
        status, resp = api_with_data.handle_request("DELETE", "/api/v1/content/1")
        assert status == 200
        assert resp["deleted"] is True
        assert "1" not in api_with_data._store

    def test_delete_not_found(self, api):
        status, _resp = api.handle_request("DELETE", "/api/v1/content/999")
        assert status == 404


# --- Search ---

class TestSearch:
    def test_search_basic(self, api_with_data):
        status, body = api_with_data.handle_request(
            "GET", "/api/v1/content/search", query_string="q=first"
        )
        assert status == 200
        assert body["total"] == 1

    def test_search_no_query(self, api_with_data):
        status, _body = api_with_data.handle_request(
            "GET", "/api/v1/content/search"
        )
        assert status == 400

    def test_search_no_results(self, api_with_data):
        _status, body = api_with_data.handle_request(
            "GET", "/api/v1/content/search", query_string="q=nonexistent"
        )
        assert body["total"] == 0


# --- Export ---

class TestExport:
    def test_export_json(self, api_with_data):
        status, body = api_with_data.handle_request(
            "GET", "/api/v1/content/export", query_string="format=json"
        )
        assert status == 200
        assert body["format"] == "json"
        assert body["total"] == 2


# --- 404 ---

class TestNotFound:
    def test_unknown_route(self, api):
        status, _body = api.handle_request("GET", "/unknown")
        assert status == 404


# --- Additional API Tests ---

class TestApiErrorHandling:
    def test_create_empty_title(self, api):
        body = json.dumps({"title": ""})
        status, resp = api.handle_request("POST", "/api/v1/content", body=body)
        assert status == 201
        assert resp["item"]["title"] == ""

    def test_update_invalid_json(self, api_with_data):
        status, _resp = api_with_data.handle_request("PUT", "/api/v1/content/1", body="bad")
        assert status == 400

    def test_update_not_dict(self, api_with_data):
        status, resp = api_with_data.handle_request("PUT", "/api/v1/content/1", body='["list"]')
        assert status == 400
        assert resp["error"] == "Request body must be a JSON object"

    def test_update_not_dict_int(self, api_with_data):
        status, resp = api_with_data.handle_request("PUT", "/api/v1/content/1", body="123")
        assert status == 400
        assert resp["error"] == "Request body must be a JSON object"

    def test_list_page_2_empty(self, api_with_data):
        _status, body = api_with_data.handle_request(
            "GET", "/api/v1/content", query_string="page=2&per_page=1"
        )
        assert len(body["items"]) == 1

    def test_stats_tags(self, api_with_data):
        _status, body = api_with_data.handle_request("GET", "/api/v1/stats")
        assert "tags" in body
        assert body["tags"]["a"] == 1

    def test_export_default_format(self, api_with_data):
        _status, body = api_with_data.handle_request("GET", "/api/v1/content/export")
        assert body["format"] == "json"

    def test_multiple_creates(self, api):
        for i in range(5):
            body = json.dumps({"title": f"Post {i}"})
            status, _ = api.handle_request("POST", "/api/v1/content", body=body)
            assert status == 201
        status, body = api.handle_request("GET", "/api/v1/content")
        assert body["total"] == 5

    def test_update_tags(self, api_with_data):
        body = json.dumps({"tags": ["new", "tags"]})
        _status, resp = api_with_data.handle_request("PUT", "/api/v1/content/1", body=body)
        assert resp["item"]["tags"] == ["new", "tags"]

    def test_update_link(self, api_with_data):
        body = json.dumps({"link": "http://new-url.com"})
        _status, resp = api_with_data.handle_request("PUT", "/api/v1/content/1", body=body)
        assert resp["item"]["link"] == "http://new-url.com"


# --- Validation Tests ---

class TestContentValidation:
    def test_validate_valid_content(self, api):
        errors = api._validate_content({"title": "Test", "tags": ["a"]})
        assert errors == []

    def test_validate_not_dict(self, api):
        errors = api._validate_content("string")
        assert len(errors) > 0

    def test_validate_title_not_string(self, api):
        errors = api._validate_content({"title": 123})
        assert any("Title" in e for e in errors)

    def test_validate_tags_not_list(self, api):
        errors = api._validate_content({"tags": "not-a-list"})
        assert any("Tags" in e for e in errors)

    def test_validate_title_too_long(self, api):
        errors = api._validate_content({"title": "x" * 201})
        assert any("200" in e for e in errors)


# --- RequestLogger Tests ---

class TestRequestLogger:
    def test_logger_records_request(self, api):
        logger = api_module.RequestLogger(api)
        logger.handle_request("GET", "/api/v1/health")
        assert len(logger.log) == 1
        assert logger.log[0]["method"] == "GET"

    def test_logger_records_status(self, api):
        logger = api_module.RequestLogger(api)
        logger.handle_request("GET", "/api/v1/health")
        assert logger.log[0]["status"] == 200

    def test_logger_multiple_requests(self, api):
        logger = api_module.RequestLogger(api)
        logger.handle_request("GET", "/api/v1/health")
        logger.handle_request("GET", "/api/v1/stats")
        assert len(logger.log) == 2

    def test_logger_clear(self, api):
        logger = api_module.RequestLogger(api)
        logger.handle_request("GET", "/api/v1/health")
        logger.clear_log()
        assert len(logger.log) == 0

    def test_logger_404(self, api):
        logger = api_module.RequestLogger(api)
        logger.handle_request("GET", "/unknown")
        assert logger.log[0]["status"] == 404

    def test_logger_has_timestamp(self, api):
        logger = api_module.RequestLogger(api)
        logger.handle_request("GET", "/api/v1/health")
        assert "timestamp" in logger.log[0]


class TestContentApiDocstring:
    def test_docstring_does_not_promise_wsgi_asgi_compatibility(self) -> None:
        """Regression: module docstring must not over-promise WSGI/ASGI.

        ContentAPI exposes a custom request/response interface
        (handle_request(method, path, body, query_string) -> (status,
        payload)); there is no WSGI __call__(environ, start_response) and no
        ASGI __call__(scope, receive, send) method, so the module docstring
        must not claim it is 'compatible with any WSGI/ASGI framework'
        (TICKET-332).
        """
        doc = (api_module.__doc__ or "").lower()
        assert "wsgi" not in doc
        assert "asgi" not in doc


# --- handle_request contract (TICKET-516) ---

class TestHandleRequestContract:
    def test_matched_route_returns_handler_tuple(self, api_with_data):
        status, body = api_with_data.handle_request("GET", "/api/v1/health")
        assert status == 200
        assert body["status"] == "healthy"

    def test_unknown_route_returns_404_guard(self, api):
        status, body = api.handle_request("GET", "/api/v1/does-not-exist")
        assert status == 404
        assert body == {"error": "Not found", "path": "/api/v1/does-not-exist"}


# --- _match_route dispatch contract (TICKET-517) ---

class TestMatchRouteDispatch:
    """Pin the _match_route dispatch contract (TICKET-517)."""

    def test_health_route_returns_health_handler(self, api):
        handler = api._match_route("GET", ["api", "v1", "health"], {}, None)
        assert handler is not None
        status, body = handler()
        assert status == 200
        assert body["status"] == "healthy"

    def test_content_item_route_returns_callable(self, api):
        handler = api._match_route("GET", ["api", "v1", "content", "42"], {}, None)
        assert handler is not None
        result = handler()
        assert isinstance(result, tuple)

    def test_unmatched_path_returns_none(self, api):
        handler = api._match_route("GET", ["api", "v1", "nonexistent"], {}, None)
        assert handler is None


class TestRouteContentDispatch:
    """Pin the _route_content dispatch contract (TICKET-519)."""

    def test_get_returns_list_handler(self, api_with_data):
        handler = api_with_data._route_content("GET", {}, None)
        assert handler is not None
        status, body = handler()
        assert status == 200
        assert body["total"] == 2
        assert body["page"] == 1
        assert body["per_page"] == 20
        assert len(body["items"]) == 2

    def test_unmatched_method_returns_none(self, api):
        handler = api._route_content("PATCH", {}, None)
        assert handler is None


class TestRouteContentItemDispatch:
    """Pin the _route_content_item dispatch contract (TICKET-520)."""

    def test_get_returns_get_handler(self, api_with_data):
        handler = api_with_data._route_content_item("GET", "1", None)
        assert handler is not None
        status, body = handler()
        assert status == 200
        assert body["item"]["id"] == "1"
        assert body["item"]["title"] == "First"

    def test_put_returns_update_handler(self, api_with_data):
        handler = api_with_data._route_content_item(
            "PUT", "1", json.dumps({"title": "Renamed"})
        )
        assert handler is not None
        status, body = handler()
        assert status == 200
        assert body["item"]["id"] == "1"
        assert body["item"]["title"] == "Renamed"

    def test_delete_returns_delete_handler(self, api_with_data):
        handler = api_with_data._route_content_item("DELETE", "1", None)
        assert handler is not None
        status, body = handler()
        assert status == 200
        assert body["deleted"] is True
        assert body["id"] == "1"
        assert "1" not in api_with_data._store

    def test_unmatched_method_returns_none(self, api):
        handler = api._route_content_item("PATCH", "1", None)
        assert handler is None

class TestListContentDocstring523:
    """Pin the _list_content pagination contract (TICKET-523)."""

    def test_docstring_states_exact_contract(self) -> None:
        doc = ContentAPI._list_content.__doc__
        assert doc is not None
        # Key contract phrases the docstring must state.
        assert "page" in doc
        assert "per_page" in doc
        assert "400" in doc
        assert "200" in doc
        assert "items" in doc
        assert "total" in doc
        assert "100" in doc
        assert "default 1" in doc
        assert "default 20" in doc


class TestGetContentDocstring524:
    """Pin the _get_content dispatch contract (TICKET-524)."""

    def test_docstring_states_exact_contract(self) -> None:
        doc = ContentAPI._get_content.__doc__
        assert doc is not None
        # Key contract phrases the docstring must state.
        assert "item_id" in doc
        assert "store" in doc
        assert "404" in doc
        assert "200" in doc
        assert "item" in doc
        assert "not found" in doc


class TestCreateContentDocstring525:
    """Pin the _create_content dispatch contract (TICKET-525)."""

    def test_docstring_states_exact_contract(self) -> None:
        doc = ContentAPI._create_content.__doc__
        assert doc is not None
        # Key contract phrases the docstring must state.
        assert "body" in doc
        assert "400" in doc
        assert "JSON" in doc
        assert "object" in doc
        assert "201" in doc
        assert "item" in doc
        assert "store" in doc


class TestUpdateContentDocstring526:
    """Pin the _update_content dispatch contract (TICKET-526)."""

    def test_docstring_states_exact_contract(self) -> None:
        doc = ContentAPI._update_content.__doc__
        assert doc is not None
        # Key contract phrases the docstring must state.
        assert "item_id" in doc
        assert "store" in doc
        assert "404" in doc
        assert "not found" in doc
        assert "body" in doc
        assert "400" in doc
        assert "JSON" in doc
        assert "object" in doc
        assert "200" in doc
        assert "item" in doc
        assert "updated_at" in doc


class TestDeleteContentDocstring527:
    """Pin the _delete_content dispatch contract (TICKET-527)."""

    def test_docstring_states_exact_contract(self) -> None:
        doc = ContentAPI._delete_content.__doc__
        assert doc is not None
        # Key contract phrases the docstring must state.
        assert "item_id" in doc
        assert "store" in doc
        assert "404" in doc
        assert "not found" in doc
        assert "200" in doc
        assert "deleted" in doc
        assert "id" in doc


class TestSearchContentDocstring528:
    """Pin the _search_content dispatch contract (TICKET-528)."""

    def test_docstring_states_exact_contract(self) -> None:
        doc = ContentAPI._search_content.__doc__
        assert doc is not None
        # Key contract phrases the docstring must state.
        assert "q" in doc
        assert "required" in doc
        assert "400" in doc
        assert "results" in doc
        assert "total" in doc
        assert "query" in doc
        assert "200" in doc


class TestExportContentDocstring529:
    """Pin the _export_content dispatch contract (TICKET-529)."""

    def test_docstring_states_exact_contract(self) -> None:
        doc = ContentAPI._export_content.__doc__
        assert doc is not None
        # Key contract phrases the docstring must state.
        assert "format" in doc
        assert "json" in doc
        assert "items" in doc
        assert "total" in doc
        assert "200" in doc


class TestHealthCheckDocstring530:
    """Pin the _health_check dispatch contract (TICKET-530)."""

    def test_docstring_states_exact_contract(self) -> None:
        doc = ContentAPI._health_check.__doc__
        assert doc is not None
        # Key contract phrases the docstring must state.
        assert "status" in doc
        assert "healthy" in doc
        assert "timestamp" in doc
        assert "200" in doc
