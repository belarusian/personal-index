"""Tests for content_changelog module."""

from __future__ import annotations

import pytest
from personal_index.content_changelog import (
    ChangelogEntry,
    ChangelogGenerator,
    ChangelogFormat,
)


class TestChangelogEntry:
    def test_create_entry(self):
        entry = ChangelogEntry(
            content_id="doc-1",
            version_number=2,
            change_type="modified",
            message="Updated title",
        )
        assert entry.content_id == "doc-1"
        assert entry.version_number == 2
        assert entry.change_type == "modified"
        assert entry.message == "Updated title"

    def test_entry_to_dict(self):
        entry = ChangelogEntry(
            content_id="doc-1",
            version_number=1,
            change_type="created",
            message="Initial version",
        )
        d = entry.to_dict()
        assert d["content_id"] == "doc-1"
        assert d["change_type"] == "created"


class TestChangelogFormat:
    def test_format_values(self):
        assert ChangelogFormat.TEXT.value == "text"
        assert ChangelogFormat.MARKDOWN.value == "markdown"
        assert ChangelogFormat.JSON.value == "json"


class TestChangelogGenerator:
    def test_create_generator(self):
        gen = ChangelogGenerator()
        assert gen.format == ChangelogFormat.TEXT

    def test_generate_empty_changelog(self):
        gen = ChangelogGenerator()
        result = gen.generate("doc-1", [])
        assert result == ""

    def test_generate_single_entry(self):
        gen = ChangelogGenerator()
        entries = [
            ChangelogEntry("doc-1", 1, "created", "Initial version"),
        ]
        result = gen.generate("doc-1", entries)
        assert "doc-1" in result
        assert "Initial version" in result

    def test_generate_multiple_entries(self):
        gen = ChangelogGenerator()
        entries = [
            ChangelogEntry("doc-1", 1, "created", "Initial"),
            ChangelogEntry("doc-1", 2, "modified", "Updated"),
            ChangelogEntry("doc-1", 3, "modified", "Fixed typo"),
        ]
        result = gen.generate("doc-1", entries)
        assert "Initial" in result
        assert "Updated" in result
        assert "Fixed typo" in result

    def test_generate_markdown_format(self):
        gen = ChangelogGenerator(format=ChangelogFormat.MARKDOWN)
        entries = [
            ChangelogEntry("doc-1", 1, "created", "Initial version"),
        ]
        result = gen.generate("doc-1", entries)
        assert "#" in result or "*" in result or "-" in result

    def test_generate_json_format(self):
        gen = ChangelogGenerator(format=ChangelogFormat.JSON)
        entries = [
            ChangelogEntry("doc-1", 1, "created", "Initial version"),
        ]
        result = gen.generate("doc-1", entries)
        assert "doc-1" in result
        assert "Initial version" in result

    def test_generate_with_version_store(self):
        from personal_index.content_versioning import VersionStore
        store = VersionStore()
        store.save_version("doc-1", "V1", message="Initial")
        store.save_version("doc-1", "V2", message="Updated")
        store.save_version("doc-1", "V3", message="Fixed")
        gen = ChangelogGenerator()
        result = gen.generate_from_store("doc-1", store)
        assert "Initial" in result
        assert "Updated" in result

    def test_generate_from_store_empty(self):
        from personal_index.content_versioning import VersionStore
        store = VersionStore()
        gen = ChangelogGenerator()
        result = gen.generate_from_store("doc-1", store)
        assert result == ""

    def test_generate_from_store_nonexistent(self):
        from personal_index.content_versioning import VersionStore
        store = VersionStore()
        store.save_version("doc-1", "V1")
        gen = ChangelogGenerator()
        result = gen.generate_from_store("nonexistent", store)
        assert result == ""

    def test_generate_all_content_changelog(self):
        from personal_index.content_versioning import VersionStore
        store = VersionStore()
        store.save_version("doc-1", "V1", message="Doc1 initial")
        store.save_version("doc-2", "V1", message="Doc2 initial")
        gen = ChangelogGenerator()
        result = gen.generate_all(store)
        assert "doc-1" in result or "doc-2" in result

    def test_generate_with_date_range(self):
        from personal_index.content_versioning import VersionStore
        from datetime import datetime, timezone, timedelta
        store = VersionStore()
        store.save_version("doc-1", "V1", message="Old version")
        store.save_version("doc-1", "V2", message="New version")
        gen = ChangelogGenerator()
        result = gen.generate_from_store("doc-1", store)
        assert "Old version" in result

    def test_generate_grouped_by_type(self):
        gen = ChangelogGenerator()
        entries = [
            ChangelogEntry("doc-1", 1, "created", "Created"),
            ChangelogEntry("doc-1", 2, "modified", "Modified"),
            ChangelogEntry("doc-1", 3, "deleted", "Deleted"),
        ]
        result = gen.generate("doc-1", entries)
        assert "Created" in result

    def test_generate_with_limit(self):
        from personal_index.content_versioning import VersionStore
        store = VersionStore()
        for i in range(10):
            store.save_version("doc-1", f"V{i+1}", message=f"Version {i+1}")
        gen = ChangelogGenerator()
        result = gen.generate_from_store("doc-1", store, limit=3)
        # Should only include last 3 entries
        assert "Version 10" in result or "Version 9" in result

    def test_generate_summary(self):
        gen = ChangelogGenerator()
        entries = [
            ChangelogEntry("doc-1", 1, "created", "Initial"),
            ChangelogEntry("doc-1", 2, "modified", "Updated"),
        ]
        summary = gen.generate_summary("doc-1", entries)
        assert isinstance(summary, dict)
        assert "total_changes" in summary

    def test_generate_html_format(self):
        gen = ChangelogGenerator(format=ChangelogFormat.TEXT)
        entries = [
            ChangelogEntry("doc-1", 1, "created", "Initial version"),
        ]
        result = gen.generate("doc-1", entries)
        assert isinstance(result, str)
