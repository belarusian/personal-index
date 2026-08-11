"""Tests for content_api module."""

import json
import pytest
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
        status, body = api_with_data.handle_request(
            "GET", "/api/v1/content", query_string="per_page=999"
        )
        assert body["per_page"] == 100


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
        status, resp = api.handle_request("POST", "/api/v1/content", body="not json")
        assert status == 400

    def test_create_not_dict(self, api):
        status, resp = api.handle_request("POST", "/api/v1/content", body='["list"]')
        assert status == 400

    def test_create_with_tags(self, api):
        body = json.dumps({"title": "T", "tags": ["x", "y"]})
        status, resp = api.handle_request("POST", "/api/v1/content", body=body)
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
        status, body = api.handle_request("GET", "/api/v1/content/999")
        assert status == 404


# --- Update Content ---

class TestUpdateContent:
    def test_update_existing(self, api_with_data):
        body = json.dumps({"title": "Updated"})
        status, resp = api_with_data.handle_request("PUT", "/api/v1/content/1", body=body)
        assert status == 200
        assert resp["item"]["title"] == "Updated"

    def test_update_not_found(self, api):
        status, resp = api.handle_request("PUT", "/api/v1/content/999", body='{}')
        assert status == 404

    def test_update_no_body(self, api_with_data):
        status, resp = api_with_data.handle_request("PUT", "/api/v1/content/1")
        assert status == 400

    def test_update_preserves_other_fields(self, api_with_data):
        body = json.dumps({"title": "New Title"})
        status, resp = api_with_data.handle_request("PUT", "/api/v1/content/1", body=body)
        assert resp["item"]["description"] == "Desc 1"


# --- Delete Content ---

class TestDeleteContent:
    def test_delete_existing(self, api_with_data):
        status, resp = api_with_data.handle_request("DELETE", "/api/v1/content/1")
        assert status == 200
        assert resp["deleted"] is True
        assert "1" not in api_with_data._store

    def test_delete_not_found(self, api):
        status, resp = api.handle_request("DELETE", "/api/v1/content/999")
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
        status, body = api_with_data.handle_request(
            "GET", "/api/v1/content/search"
        )
        assert status == 400

    def test_search_no_results(self, api_with_data):
        status, body = api_with_data.handle_request(
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
        status, body = api.handle_request("GET", "/unknown")
        assert status == 404
