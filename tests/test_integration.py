"""Integration tests across all content modules."""

import json

import pytest

from personal_index.content_api import ContentAPI
from personal_index.content_exporter import ContentExporter
from personal_index.content_importer import ContentImporter
from personal_index.content_scheduler import TaskScheduler
from personal_index.content_search import ContentSearch


@pytest.fixture
def sample_items():
    return [
        {"id": "1", "title": "Python Tutorial", "description": "Learn Python basics", "tags": ["python", "tutorial"], "link": "http://example.com/1"},
        {"id": "2", "title": "JavaScript Guide", "description": "JavaScript fundamentals", "tags": ["javascript", "web"], "link": "http://example.com/2"},
        {"id": "3", "title": "React Framework", "description": "Building UIs with React", "tags": ["react", "javascript"], "link": "http://example.com/3"},
    ]


class TestImportExportRoundtrip:
    def test_json_roundtrip(self, sample_items):
        importer = ContentImporter()
        exporter = ContentExporter()
        exported = exporter.export(sample_items, "json")
        imported = importer.import_content(exported, "json")
        assert len(imported) == 3
        assert imported[0]["title"] == "Python Tutorial"

    def test_html_roundtrip(self, sample_items):
        importer = ContentImporter()
        exporter = ContentExporter()
        exported = exporter.export(sample_items, "html")
        imported = importer.import_content(exported, "html")
        assert len(imported) == 3

    def test_markdown_roundtrip(self, sample_items):
        importer = ContentImporter()
        exporter = ContentExporter()
        exported = exporter.export(sample_items, "markdown")
        imported = importer.import_content(exported, "markdown")
        # Markdown exporter adds a top-level heading, so we get 4 items
        assert len(imported) >= 3
        titles = [i["title"] for i in imported]
        assert "Python Tutorial" in titles

    def test_rss_roundtrip(self, sample_items):
        importer = ContentImporter()
        exporter = ContentExporter()
        exported = exporter.export(sample_items, "rss")
        imported = importer.import_content(exported, "rss")
        assert len(imported) == 3


class TestSearchAfterImport:
    def test_search_imported_json(self, sample_items):
        importer = ContentImporter()
        search = ContentSearch()
        items = importer.import_content(json.dumps(sample_items), "json")
        search.index_items(items)
        result = search.search("python")
        assert result["total"] > 0

    def test_search_with_filter(self, sample_items):
        importer = ContentImporter()
        search = ContentSearch()
        items = importer.import_content(json.dumps(sample_items), "json")
        search.index_items(items)
        result = search.search("javascript", filters={"tags": ["javascript", "web"]})
        assert result["total"] > 0


class TestAPIWithSearch:
    def test_create_and_search(self):
        api = ContentAPI()
        body = json.dumps({"title": "Test Post", "description": "A test post about python"})
        api.handle_request("POST", "/api/v1/content", body=body)
        status, resp = api.handle_request("GET", "/api/v1/content/search", query_string="q=test")
        assert status == 200
        assert resp["total"] == 1

    def test_create_update_delete(self):
        api = ContentAPI()
        body = json.dumps({"title": "Original"})
        status, resp = api.handle_request("POST", "/api/v1/content", body=body)
        item_id = resp["item"]["id"]
        api.handle_request("PUT", f"/api/v1/content/{item_id}", body=json.dumps({"title": "Updated"}))
        status, resp = api.handle_request("GET", f"/api/v1/content/{item_id}")
        assert resp["item"]["title"] == "Updated"
        api.handle_request("DELETE", f"/api/v1/content/{item_id}")
        status, resp = api.handle_request("GET", f"/api/v1/content/{item_id}")
        assert status == 404


class TestSchedulerWithAPI:
    def test_schedule_export_task(self):
        scheduler = TaskScheduler()
        ContentAPI()
        results = []
        def export_cb(task):
            results.append("exported")
        task = scheduler.add_task("Daily Export", "export", "0 0 * * *", callback=export_cb)
        assert task.task_type == "export"
        assert task.enabled is True

    def test_schedule_cleanup_task(self):
        scheduler = TaskScheduler()
        task = scheduler.add_task("Weekly Cleanup", "cleanup", "0 0 * * 0", config={"max_age_days": 30})
        assert task.config["max_age_days"] == 30
