"""Tests for content_import_opml - import OPML bookmarks."""

from __future__ import annotations

import pytest

from personal_index.content_import_opml import (
    OPMLBookmark,
    OPMLImportResult,
    OPMLImporter,
)


# Sample OPML documents for testing
SIMPLE_OPML = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head>
    <title>My Bookmarks</title>
  </head>
  <body>
    <outline text="Google" xmlUrl="https://google.com" htmlUrl="https://google.com" title="Google Search"/>
    <outline text="GitHub" xmlUrl="https://github.com" htmlUrl="https://github.com" title="GitHub"/>
  </body>
</opml>
"""

NESTED_OPML = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head>
    <title>Nested Bookmarks</title>
  </head>
  <body>
    <outline text="Tech" title="Technology">
      <outline text="Python" xmlUrl="https://python.org" htmlUrl="https://python.org" title="Python"/>
      <outline text="Rust" xmlUrl="https://rust-lang.org" htmlUrl="https://rust-lang.org" title="Rust"/>
    </outline>
    <outline text="News" title="News Sites">
      <outline text="Hacker News" xmlUrl="https://news.ycombinator.com" htmlUrl="https://news.ycombinator.com" title="HN"/>
    </outline>
  </body>
</opml>
"""

OPML_WITH_TAGS = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head>
    <title>Tagged Bookmarks</title>
  </head>
  <body>
    <outline text="Python" xmlUrl="https://python.org" htmlUrl="https://python.org" title="Python" _tags="programming,python"/>
  </body>
</opml>
"""

OPML_WITH_DESCRIPTION = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head>
    <title>Described Bookmarks</title>
  </head>
  <body>
    <outline text="Python" xmlUrl="https://python.org" htmlUrl="https://python.org" title="Python" description="Python programming language"/>
  </body>
</opml>
"""

OPML_NO_HEAD = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <body>
    <outline text="Test" xmlUrl="https://test.com" htmlUrl="https://test.com" title="Test Site"/>
  </body>
</opml>
"""

OPML_ONLY_TEXT = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head>
    <title>Text Only</title>
  </head>
  <body>
    <outline text="Folder Only" title="A folder with no links"/>
  </body>
</opml>
"""

OPML_WITH_TYPE = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head>
    <title>With Type</title>
  </head>
  <body>
    <outline type="rss" text="Feed" xmlUrl="https://example.com/feed.xml" htmlUrl="https://example.com" title="Example Feed"/>
  </body>
</opml>
"""


class TestOPMLBookmark:
    """Tests for OPMLBookmark dataclass."""

    def test_bookmark_creation(self):
        bm = OPMLBookmark(
            url="https://example.com",
            title="Example",
            text="Example Site",
        )
        assert bm.url == "https://example.com"
        assert bm.title == "Example"
        assert bm.text == "Example Site"

    def test_bookmark_defaults(self):
        bm = OPMLBookmark(url="https://example.com")
        assert bm.title == ""
        assert bm.description == ""
        assert bm.tags == []
        assert bm.folder == ""

    def test_bookmark_with_tags(self):
        bm = OPMLBookmark(
            url="https://example.com",
            title="Example",
            tags=["tech", "web"],
        )
        assert bm.tags == ["tech", "web"]

    def test_bookmark_with_folder(self):
        bm = OPMLBookmark(
            url="https://example.com",
            title="Example",
            folder="Tech/Python",
        )
        assert bm.folder == "Tech/Python"

    def test_bookmark_to_dict(self):
        bm = OPMLBookmark(
            url="https://example.com",
            title="Example",
            description="A site",
            tags=["tech"],
            folder="Tech",
        )
        d = bm.to_dict()
        assert d["url"] == "https://example.com"
        assert d["title"] == "Example"
        assert d["tags"] == ["tech"]

    def test_bookmark_from_dict(self):
        data = {
            "url": "https://example.com",
            "title": "Example",
            "description": "A site",
            "tags": ["tech"],
            "folder": "Tech",
            "text": "Example Site",
        }
        bm = OPMLBookmark.from_dict(data)
        assert bm.url == "https://example.com"
        assert bm.title == "Example"

    def test_bookmark_repr(self):
        bm = OPMLBookmark(url="https://example.com", title="Example")
        assert "example.com" in repr(bm)


class TestOPMLImportResult:
    """Tests for OPMLImportResult dataclass."""

    def test_result_defaults(self):
        result = OPMLImportResult()
        assert result.total_imported == 0
        assert result.total_skipped == 0
        assert result.bookmarks == []

    def test_result_with_data(self):
        result = OPMLImportResult(
            total_imported=5,
            total_skipped=2,
            errors=["error1"],
        )
        assert result.total_imported == 5
        assert result.total_skipped == 2
        assert result.errors == ["error1"]

    def test_result_to_dict(self):
        result = OPMLImportResult(total_imported=3, total_skipped=1)
        d = result.to_dict()
        assert d["total_imported"] == 3
        assert d["total_skipped"] == 1

    def test_result_success(self):
        result = OPMLImportResult(total_imported=3, errors=[])
        assert result.is_success is True

    def test_result_failure(self):
        result = OPMLImportResult(total_imported=0, errors=["bad xml"])
        assert result.is_success is False


class TestOPMLImporter:
    """Tests for OPMLImporter class."""

    def setup_method(self):
        self.importer = OPMLImporter()

    def test_import_simple_opml(self):
        result = self.importer.import_opml(SIMPLE_OPML)
        assert result.total_imported == 2
        assert result.total_skipped == 0
        assert len(result.bookmarks) == 2

    def test_import_simple_opml_urls(self):
        result = self.importer.import_opml(SIMPLE_OPML)
        urls = [b.url for b in result.bookmarks]
        assert "https://google.com" in urls
        assert "https://github.com" in urls

    def test_import_simple_opml_titles(self):
        result = self.importer.import_opml(SIMPLE_OPML)
        titles = [b.title for b in result.bookmarks]
        assert "Google Search" in titles
        assert "GitHub" in titles

    def test_import_nested_opml(self):
        result = self.importer.import_opml(NESTED_OPML)
        assert result.total_imported == 3
        folders = [b.folder for b in result.bookmarks]
        assert "Tech" in folders
        assert "News" in folders

    def test_import_nested_opml_folder_paths(self):
        result = self.importer.import_opml(NESTED_OPML)
        python = [b for b in result.bookmarks if b.url == "https://python.org"][0]
        assert python.folder == "Tech"

    def test_import_opml_with_tags(self):
        result = self.importer.import_opml(OPML_WITH_TAGS)
        assert result.total_imported == 1
        bm = result.bookmarks[0]
        assert "programming" in bm.tags
        assert "python" in bm.tags

    def test_import_opml_with_description(self):
        result = self.importer.import_opml(OPML_WITH_DESCRIPTION)
        assert result.total_imported == 1
        bm = result.bookmarks[0]
        assert bm.description == "Python programming language"

    def test_import_opml_no_head(self):
        result = self.importer.import_opml(OPML_NO_HEAD)
        assert result.total_imported == 1

    def test_import_opml_only_text_outlines(self):
        result = self.importer.import_opml(OPML_ONLY_TEXT)
        assert result.total_imported == 0
        assert result.total_skipped == 0

    def test_import_opml_with_type(self):
        result = self.importer.import_opml(OPML_WITH_TYPE)
        assert result.total_imported == 1
        bm = result.bookmarks[0]
        assert bm.outline_type == "rss"

    def test_import_invalid_xml(self):
        result = self.importer.import_opml("not xml at all")
        assert result.total_imported == 0
        assert len(result.errors) > 0

    def test_import_empty_string(self):
        result = self.importer.import_opml("")
        assert result.total_imported == 0
        assert len(result.errors) > 0

    def test_import_opml_prefers_xml_url(self):
        result = self.importer.import_opml(SIMPLE_OPML)
        bm = result.bookmarks[0]
        assert bm.url == "https://google.com"

    def test_import_opml_falls_back_to_html_url(self):
        fallback_opml = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <body>
    <outline text="Site" htmlUrl="https://example.com" title="Example"/>
  </body>
</opml>
"""
        result = self.importer.import_opml(fallback_opml)
        assert result.total_imported == 1
        assert result.bookmarks[0].url == "https://example.com"

    def test_import_opml_falls_back_to_text_for_title(self):
        fallback_opml = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <body>
    <outline text="Fallback Title" xmlUrl="https://example.com"/>
  </body>
</opml>
"""
        result = self.importer.import_opml(fallback_opml)
        assert result.total_imported == 1
        assert result.bookmarks[0].title == "Fallback Title"

    def test_import_opml_deduplicates_urls(self):
        dup_opml = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <body>
    <outline text="Google" xmlUrl="https://google.com" htmlUrl="https://google.com" title="Google"/>
    <outline text="Google Again" xmlUrl="https://google.com" htmlUrl="https://google.com" title="Google Again"/>
  </body>
</opml>
"""
        result = self.importer.import_opml(dup_opml)
        assert result.total_imported == 1
        assert result.total_skipped == 1

    def test_import_opml_with_manager(self):
        from personal_index.bookmarks import BookmarkManager
        manager = BookmarkManager()
        importer = OPMLImporter(manager=manager)
        result = importer.import_opml(SIMPLE_OPML)
        assert result.total_imported == 2
        assert manager.count() == 2

    def test_import_opml_empty_body(self):
        empty_opml = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head><title>Empty</title></head>
  <body/>
</opml>
"""
        result = self.importer.import_opml(empty_opml)
        assert result.total_imported == 0

    def test_import_opml_deeply_nested(self):
        deep_opml = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <body>
    <outline text="Level1">
      <outline text="Level2">
        <outline text="Level3">
          <outline text="Site" xmlUrl="https://deep.com" title="Deep Site"/>
        </outline>
      </outline>
    </outline>
  </body>
</opml>
"""
        result = self.importer.import_opml(deep_opml)
        assert result.total_imported == 1
        bm = result.bookmarks[0]
        assert "Level3" in bm.folder

    def test_import_opml_head_metadata(self):
        result = self.importer.import_opml(SIMPLE_OPML)
        assert result.source_title == "My Bookmarks"

    def test_import_opml_without_head_metadata(self):
        result = self.importer.import_opml(OPML_NO_HEAD)
        assert result.source_title == ""
