"""Tests for content_importer module."""

import pytest
from personal_index.content_importer import ContentImporter


@pytest.fixture
def importer():
    return ContentImporter()


# --- JSON Import Tests ---

class TestJsonImport:
    def test_import_json_list(self, importer):
        data = '[{"title": "Post 1", "description": "Desc 1", "link": "http://a.com"}]'
        items = importer.import_content(data, "json")
        assert len(items) == 1
        assert items[0]["title"] == "Post 1"

    def test_import_json_single_dict(self, importer):
        data = '{"title": "Single", "description": "One item"}'
        items = importer.import_content(data, "json")
        assert len(items) == 1
        assert items[0]["title"] == "Single"

    def test_import_json_empty_list(self, importer):
        items = importer.import_content("[]", "json")
        assert items == []

    def test_import_json_with_tags(self, importer):
        data = '[{"title": "T", "tags": ["a", "b"]}]'
        items = importer.import_content(data, "json")
        assert items[0]["tags"] == ["a", "b"]

    def test_import_json_missing_fields(self, importer):
        data = '[{}]'
        items = importer.import_content(data, "json")
        assert items[0]["title"] == "Untitled"
        assert items[0]["description"] == ""

    def test_import_json_case_insensitive(self, importer):
        data = '[{"title": "Test"}]'
        items = importer.import_content(data, "JSON")
        assert len(items) == 1


# --- CSV Import Tests ---

class TestCsvImport:
    def test_import_csv_basic(self, importer):
        data = "title,description,link\nPost 1,Desc 1,http://a.com\nPost 2,Desc 2,http://b.com"
        items = importer.import_content(data, "csv")
        assert len(items) == 2
        assert items[0]["title"] == "Post 1"

    def test_import_csv_empty(self, importer):
        data = "title,description\n"
        items = importer.import_content(data, "csv")
        assert items == []

    def test_import_csv_custom_headers(self, importer):
        data = "name,url\nMy Post,http://x.com"
        items = importer.import_content(data, "csv")
        assert items[0]["name"] == "My Post"
