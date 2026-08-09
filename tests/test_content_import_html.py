"""Tests for content_import_html - import Netscape HTML bookmarks."""

from __future__ import annotations

import pytest

from personal_index.content_import_html import (
    HTMLBookmark,
    HTMLImportResult,
    HTMLImporter,
)


# Sample Netscape HTML bookmark files
SIMPLE_HTML = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<title>Bookmarks</title>
</head>
<body>
<h1>Bookmarks</h1>
<dl><p>
    <dt><a href="https://google.com" add_date="1609459200">Google</a>
    <dt><a href="https://github.com" add_date="1609459200">GitHub</a>
</dl><p>
</body>
</html>
"""

NESTED_HTML = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<html>
<head><title>Bookmarks</title></head>
<body>
<h1>Bookmarks</h1>
<dl><p>
    <dt><h3>Technology</h3>
    <dl><p>
        <dt><a href="https://python.org" add_date="1609459200">Python</a>
        <dt><a href="https://rust-lang.org" add_date="1609459200">Rust</a>
    </dl><p>
    <dt><h3>News</h3>
    <dl><p>
        <dt><a href="https://news.ycombinator.com" add_date="1609459200">Hacker News</a>
    </dl><p>
</dl><p>
</body>
</html>
"""

HTML_WITH_DESCRIPTION = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<html>
<head><title>Bookmarks</title></head>
<body>
<dl><p>
    <dt><a href="https://example.com" add_date="1609459200" icon="data:image/png">Example Site</a>
    <dd>This is a description
</dl><p>
</body>
</html>
"""

HTML_WITH_TAGS = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<html>
<head><title>Bookmarks</title></head>
<body>
<dl><p>
    <dt><a href="https://example.com" add_date="1609459200" tags="tech,web,python">Example</a>
</dl><p>
</body>
</html>
"""

HTML_WITH_LAST_MODIFIED = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<html>
<head><title>Bookmarks</title></head>
<body>
<dl><p>
    <dt><a href="https://example.com" add_date="1609459200" last_modified="1640995200">Example</a>
</dl><p>
</body>
</html>
"""

HTML_WITH_INDEX = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<html>
<head><title>Bookmarks</title></head>
<body>
<dl><p>
    <dt><a href="https://example.com" add_date="1609459200" index="1">Example</a>
</dl><p>
</body>
</html>
"""

HTML_WITH_FAVICON = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<html>
<head><title>Bookmarks</title></head>
<body>
<dl><p>
    <dt><a href="https://example.com" add_date="1609459200" icon="https://example.com/favicon.ico">Example</a>
</dl><p>
</body>
</html>
"""

HTML_DEEP_NESTED = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<html>
<head><title>Bookmarks</title></head>
<body>
<dl><p>
    <dt><h3>Level1</h3>
    <dl><p>
        <dt><h3>Level2</h3>
        <dl><p>
            <dt><h3>Level3</h3>
            <dl><p>
                <dt><a href="https://deep.com" add_date="1609459200">Deep Site</a>
            </dl><p>
        </dl><p>
    </dl><p>
</dl><p>
</body>
</html>
"""

HTML_MIXED = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<html>
<head><title>Bookmarks</title></head>
<body>
<dl><p>
    <dt><a href="https://root.com" add_date="1609459200">Root Link</a>
    <dt><h3>Folder</h3>
    <dl><p>
        <dt><a href="https://nested.com" add_date="1609459200">Nested Link</a>
        <dt><h3>Subfolder</h3>
        <dl><p>
            <dt><a href="https://sub.com" add_date="1609459200">Sub Link</a>
        </dl><p>
    </dl><p>
</dl><p>
</body>
</html>
"""

HTML_EMPTY = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<html>
<head><title>Bookmarks</title></head>
<body>
</body>
</html>
"""

HTML_WITH_HR = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<html>
<head><title>Bookmarks</title></head>
<body>
<dl><p>
    <dt><a href="https://example.com" add_date="1609459200">Example</a>
    <hr>
    <dt><a href="https://other.com" add_date="1609459200">Other</a>
</dl><p>
</body>
</html>
"""


class TestHTMLBookmark:
    """Tests for HTMLBookmark dataclass."""

    def test_bookmark_creation(self):
        bm = HTMLBookmark(url="https://example.com", title="Example")
        assert bm.url == "https://example.com"
        assert bm.title == "Example"

    def test_bookmark_defaults(self):
        bm = HTMLBookmark(url="https://example.com")
        assert bm.title == ""
        assert bm.description == ""
        assert bm.tags == []
        assert bm.folder == ""

    def test_bookmark_with_all_fields(self):
        bm = HTMLBookmark(
            url="https://example.com",
            title="Example",
            description="A site",
            tags=["tech"],
            folder="Tech",
            add_date="1609459200",
            last_modified="1640995200",
            icon="https://example.com/favicon.ico",
        )
        assert bm.description == "A site"
        assert bm.tags == ["tech"]
        assert bm.folder == "Tech"
        assert bm.add_date == "1609459200"

    def test_bookmark_to_dict(self):
        bm = HTMLBookmark(
            url="https://example.com",
            title="Example",
            tags=["tech"],
            folder="Tech",
        )
        d = bm.to_dict()
        assert d["url"] == "https://example.com"
        assert d["tags"] == ["tech"]

    def test_bookmark_from_dict(self):
        data = {
            "url": "https://example.com",
            "title": "Example",
            "description": "A site",
            "tags": ["tech"],
            "folder": "Tech",
            "add_date": "1609459200",
            "last_modified": "1640995200",
            "icon": "https://example.com/favicon.ico",
        }
        bm = HTMLBookmark.from_dict(data)
        assert bm.url == "https://example.com"
        assert bm.title == "Example"

    def test_bookmark_repr(self):
        bm = HTMLBookmark(url="https://example.com", title="Example")
        assert "example.com" in repr(bm)


class TestHTMLImportResult:
    """Tests for HTMLImportResult dataclass."""

    def test_result_defaults(self):
        result = HTMLImportResult()
        assert result.total_imported == 0
        assert result.bookmarks == []

    def test_result_with_data(self):
        result = HTMLImportResult(
            total_imported=5,
            total_skipped=2,
            errors=["error1"],
        )
        assert result.total_imported == 5
        assert result.errors == ["error1"]

    def test_result_to_dict(self):
        result = HTMLImportResult(total_imported=3)
        d = result.to_dict()
        assert d["total_imported"] == 3

    def test_result_is_success(self):
        result = HTMLImportResult(total_imported=3, errors=[])
        assert result.is_success is True

    def test_result_is_failure(self):
        result = HTMLImportResult(errors=["bad html"])
        assert result.is_success is False


class TestHTMLImporter:
    """Tests for HTMLImporter class."""

    def setup_method(self):
        self.importer = HTMLImporter()

    def test_import_simple_html(self):
        result = self.importer.import_html(SIMPLE_HTML)
        assert result.total_imported == 2
        urls = [b.url for b in result.bookmarks]
        assert "https://google.com" in urls
        assert "https://github.com" in urls

    def test_import_simple_html_titles(self):
        result = self.importer.import_html(SIMPLE_HTML)
        titles = [b.title for b in result.bookmarks]
        assert "Google" in titles
        assert "GitHub" in titles

    def test_import_nested_html(self):
        result = self.importer.import_html(NESTED_HTML)
        assert result.total_imported == 3
        folders = [b.folder for b in result.bookmarks]
        assert "Technology" in folders
        assert "News" in folders

    def test_import_html_with_description(self):
        result = self.importer.import_html(HTML_WITH_DESCRIPTION)
        assert result.total_imported == 1
        bm = result.bookmarks[0]
        assert bm.description == "This is a description"

    def test_import_html_with_tags(self):
        result = self.importer.import_html(HTML_WITH_TAGS)
        assert result.total_imported == 1
        bm = result.bookmarks[0]
        assert "tech" in bm.tags
        assert "web" in bm.tags
        assert "python" in bm.tags

    def test_import_html_with_last_modified(self):
        result = self.importer.import_html(HTML_WITH_LAST_MODIFIED)
        assert result.total_imported == 1
        bm = result.bookmarks[0]
        assert bm.last_modified == "1640995200"

    def test_import_html_with_index(self):
        result = self.importer.import_html(HTML_WITH_INDEX)
        assert result.total_imported == 1

    def test_import_html_with_favicon(self):
        result = self.importer.import_html(HTML_WITH_FAVICON)
        assert result.total_imported == 1
        bm = result.bookmarks[0]
        assert bm.icon == "https://example.com/favicon.ico"

    def test_import_html_deep_nested(self):
        result = self.importer.import_html(HTML_DEEP_NESTED)
        assert result.total_imported == 1
        bm = result.bookmarks[0]
        assert "Level3" in bm.folder

    def test_import_html_mixed(self):
        result = self.importer.import_html(HTML_MIXED)
        assert result.total_imported == 3
        urls = [b.url for b in result.bookmarks]
        assert "https://root.com" in urls
        assert "https://nested.com" in urls
        assert "https://sub.com" in urls

    def test_import_html_empty(self):
        result = self.importer.import_html(HTML_EMPTY)
        assert result.total_imported == 0

    def test_import_html_with_hr(self):
        result = self.importer.import_html(HTML_WITH_HR)
        assert result.total_imported == 2

    def test_import_invalid_html(self):
        result = self.importer.import_html("not html at all")
        assert result.total_imported == 0
        assert len(result.errors) > 0

    def test_import_empty_string(self):
        result = self.importer.import_html("")
        assert result.total_imported == 0
        assert len(result.errors) > 0

    def test_import_html_deduplicates(self):
        dup_html = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<html>
<body>
<dl><p>
    <dt><a href="https://example.com">Link 1</a>
    <dt><a href="https://example.com">Link 2</a>
</dl><p>
</body>
</html>
"""
        result = self.importer.import_html(dup_html)
        assert result.total_imported == 1
        assert result.total_skipped == 1

    def test_import_html_with_manager(self):
        from personal_index.bookmarks import BookmarkManager
        manager = BookmarkManager()
        importer = HTMLImporter(manager=manager)
        result = importer.import_html(SIMPLE_HTML)
        assert result.total_imported == 2
        assert manager.count() == 2

    def test_import_html_folder_paths(self):
        result = self.importer.import_html(HTML_MIXED)
        sub = [b for b in result.bookmarks if b.url == "https://sub.com"][0]
        assert "Subfolder" in sub.folder

    def test_import_html_add_date(self):
        result = self.importer.import_html(SIMPLE_HTML)
        bm = result.bookmarks[0]
        assert bm.add_date == "1609459200"

    def test_import_html_charset(self):
        charset_html = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<title>Bookmarks</title>
</head>
<body>
<dl><p>
    <dt><a href="https://example.com">Example</a>
</dl><p>
</body>
</html>
"""
        result = self.importer.import_html(charset_html)
        assert result.total_imported == 1

    def test_import_html_data_icon_ignored(self):
        result = self.importer.import_html(HTML_WITH_DESCRIPTION)
        bm = result.bookmarks[0]
        # data: URIs should not be stored as icon
        assert not bm.icon.startswith("data:")

    def test_import_html_multiple_descriptions(self):
        multi_desc = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<html>
<body>
<dl><p>
    <dt><a href="https://example.com">Example</a>
    <dd>First description
    <dd>Second description
</dl><p>
</body>
</html>
"""
        result = self.importer.import_html(multi_desc)
        assert result.total_imported == 1
        # Should capture at least one description
        assert result.bookmarks[0].description != ""
