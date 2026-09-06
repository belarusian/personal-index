"""Tests for content_importer module."""

import json

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


# --- HTML Import Tests ---

class TestHtmlImport:
    def test_import_html_articles(self, importer):
        data = "<html><body><article><h2>Title 1</h2><p>Description 1</p></article></body></html>"
        items = importer.import_content(data, "html")
        assert len(items) == 1
        assert items[0]["title"] == "Title 1"

    def test_import_html_multiple_articles(self, importer):
        data = (
            "<article><h2>A</h2><p>Desc A</p></article>"
            "<article><h2>B</h2><p>Desc B</p></article>"
        )
        items = importer.import_content(data, "html")
        assert len(items) == 2

    def test_import_html_with_link(self, importer):
        data = '<article><h2><a href="http://x.com">Title</a></h2><p>Desc</p></article>'
        items = importer.import_content(data, "html")
        assert items[0]["link"] == "http://x.com"

    def test_import_html_fallback_h2_p(self, importer):
        data = "<h2>Heading</h2><p>Paragraph</p>"
        items = importer.import_content(data, "html")
        assert len(items) == 1
        assert items[0]["title"] == "Heading"

    def test_import_html_empty(self, importer):
        items = importer.import_content("<html></html>", "html")
        assert items == []


# --- Markdown Import Tests ---

class TestMarkdownImport:
    def test_import_markdown_basic(self, importer):
        data = "## Post 1\n\nDescription here\n\n## Post 2\n\nAnother desc"
        items = importer.import_content(data, "markdown")
        assert len(items) == 2
        assert items[0]["title"] == "Post 1"

    def test_import_markdown_with_links(self, importer):
        data = "## [Linked Post](http://example.com)\n\nSome text"
        items = importer.import_content(data, "markdown")
        assert items[0]["title"] == "Linked Post"
        assert items[0]["link"] == "http://example.com"

    def test_import_markdown_empty(self, importer):
        items = importer.import_content("", "markdown")
        assert items == []

    def test_import_markdown_multiline_desc(self, importer):
        data = "## Post\n\nLine 1\nLine 2\nLine 3"
        items = importer.import_content(data, "markdown")
        assert "Line 1" in items[0]["description"]
        assert "Line 3" in items[0]["description"]

    def test_import_markdown_h1_heading(self, importer):
        data = "# Main Title\n\n## Section 1\n\nContent"
        items = importer.import_content(data, "markdown")
        assert len(items) == 2
        assert items[0]["title"] == "Main Title"


# --- RSS Import Tests ---

class TestRssImport:
    def test_import_rss_basic(self, importer):
        data = (
            '<?xml version="1.0"?><rss version="2.0"><channel>'
            '<item><title>Post 1</title><link>http://a.com</link>'
            '<description>Desc 1</description><guid>1</guid></item>'
            '</channel></rss>'
        )
        items = importer.import_content(data, "rss")
        assert len(items) == 1
        assert items[0]["title"] == "Post 1"

    def test_import_rss_multiple_items(self, importer):
        data = (
            '<rss version="2.0"><channel>'
            '<item><title>A</title><link>http://a</link><description>DA</description><guid>1</guid></item>'
            '<item><title>B</title><link>http://b</link><description>DB</description><guid>2</guid></item>'
            '</channel></rss>'
        )
        items = importer.import_content(data, "rss")
        assert len(items) == 2

    def test_import_rss_empty(self, importer):
        data = '<rss version="2.0"><channel></channel></rss>'
        items = importer.import_content(data, "rss")
        assert items == []

    def test_import_rss_missing_guid(self, importer):
        data = '<rss version="2.0"><channel><item><title>T</title></item></channel></rss>'
        items = importer.import_content(data, "rss")
        assert items[0]["title"] == "T"
        assert items[0]["id"] != ""


# --- Edge Cases & Validation ---

class TestEdgeCases:
    def test_unsupported_format_raises(self, importer):
        with pytest.raises(ValueError, match="Unsupported format"):
            importer.import_content("", "xml")

    def test_supported_formats(self):
        assert ContentImporter.SUPPORTED_FORMATS == ("json", "html", "markdown", "rss", "csv")

    def test_import_json_invalid(self, importer):
        # Malformed JSON raises a clean ValueError (module contract), not a raw
        # json.JSONDecodeError traceback.
        with pytest.raises(ValueError, match="Malformed JSON"):
            importer.import_content("not json", "json")

    def test_import_json_malformed_no_jsondecodeerror_escapes(self, importer):
        # Regression: a raw json.JSONDecodeError must not escape the public API.
        with pytest.raises(ValueError) as excinfo:
            importer.import_content("{not json", "json")
        assert not isinstance(excinfo.value, json.JSONDecodeError)

    def test_import_csv_with_empty_values(self, importer):
        data = "title,description\nPost 1,\n,Desc 2"
        items = importer.import_content(data, "csv")
        assert len(items) == 2

    def test_import_markdown_no_sections(self, importer):
        items = importer.import_content("Just plain text", "markdown")
        assert items == []

    def test_import_json_normalizes_tags(self, importer):
        data = '[{"title": "T", "tags": ["x", "y"], "extra": "ignored"}]'
        items = importer.import_content(data, "json")
        assert items[0]["tags"] == ["x", "y"]
        assert "extra" not in items[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# --- Batch Import Tests ---

class TestBatchImport:
    def test_batch_import_json_and_csv(self, importer):
        json_data = '[{"title": "JSON Post"}]'
        csv_data = "title,description\nCSV Post,From CSV"
        items = importer.batch_import([
            (json_data, "json"),
            (csv_data, "csv"),
        ])
        assert len(items) == 2
        titles = [i["title"] for i in items]
        assert "JSON Post" in titles
        assert "CSV Post" in titles

    def test_batch_import_empty(self, importer):
        items = importer.batch_import([])
        assert items == []

    def test_batch_import_single_source(self, importer):
        items = importer.batch_import([('{"title": "T"}', "json")])
        assert len(items) == 1


class TestImportContentPinning:
    """Pinning tests for ContentImporter.import_content (TICKET-465)."""

    def test_format_normalized_lower_and_strip(self, importer):
        # "  JSON  " must be accepted: lower().strip() -> "json".
        items = importer.import_content('[{"title": "T"}]', "  JSON  ")
        assert len(items) == 1
        assert items[0]["title"] == "T"

    def test_format_case_insensitive(self, importer):
        items = importer.import_content('[{"title": "T"}]', "Json")
        assert len(items) == 1

    def test_unsupported_format_raises_valueerror(self, importer):
        with pytest.raises(ValueError, match="Unsupported format"):
            importer.import_content("", "xml")

    def test_unsupported_format_message_lists_supported(self, importer):
        with pytest.raises(ValueError) as excinfo:
            importer.import_content("", "pdf")
        msg = str(excinfo.value)
        for fmt in ContentImporter.SUPPORTED_FORMATS:
            assert fmt in msg

    def test_dispatches_to_private_handler(self, importer):
        # Each supported format routes to its _import_{fmt} handler.
        for fmt in ContentImporter.SUPPORTED_FORMATS:
            assert hasattr(importer, f"_import_{fmt}")

    def test_returns_handler_result_unchanged(self, importer):
        items = importer.import_content('[{"title": "A"}, {"title": "B"}]', "json")
        assert [i["title"] for i in items] == ["A", "B"]
