"""Tests for content_diff module."""

from __future__ import annotations

import pytest
from personal_index.content_diff import (
    DiffEngine,
    DiffResult,
    DiffLine,
    DiffType,
)


class TestDiffType:
    def test_diff_type_values(self):
        assert DiffType.ADDED.value == "added"
        assert DiffType.REMOVED.value == "removed"
        assert DiffType.UNCHANGED.value == "unchanged"


class TestDiffLine:
    def test_create_diff_line(self):
        line = DiffLine(DiffType.ADDED, 1, "new line")
        assert line.diff_type == DiffType.ADDED
        assert line.line_number == 1
        assert line.text == "new line"

    def test_diff_line_to_dict(self):
        line = DiffLine(DiffType.REMOVED, 5, "old line")
        d = line.to_dict()
        assert d["diff_type"] == "removed"
        assert d["line_number"] == 5
        assert d["text"] == "old line"


class TestDiffResult:
    def test_create_diff_result(self):
        result = DiffResult(
            content_id="doc-1",
            from_version=1,
            to_version=2,
            lines=[],
            summary={"added": 0, "removed": 0, "unchanged": 0},
        )
        assert result.content_id == "doc-1"
        assert result.from_version == 1
        assert result.to_version == 2
        assert result.has_changes is False

    def test_diff_result_has_changes(self):
        lines = [
            DiffLine(DiffType.ADDED, 1, "new"),
            DiffLine(DiffType.REMOVED, 1, "old"),
        ]
        result = DiffResult(
            content_id="doc-1",
            from_version=1,
            to_version=2,
            lines=lines,
            summary={"added": 1, "removed": 1, "unchanged": 0},
        )
        assert result.has_changes is True

    def test_diff_result_to_dict(self):
        result = DiffResult(
            content_id="doc-1",
            from_version=1,
            to_version=2,
            lines=[],
            summary={"added": 0, "removed": 0, "unchanged": 0},
        )
        d = result.to_dict()
        assert d["content_id"] == "doc-1"
        assert d["from_version"] == 1
        assert d["to_version"] == 2

    def test_diff_result_line_count(self):
        lines = [
            DiffLine(DiffType.ADDED, 1, "a"),
            DiffLine(DiffType.UNCHANGED, 2, "b"),
            DiffLine(DiffType.REMOVED, 3, "c"),
        ]
        result = DiffResult(
            content_id="doc-1",
            from_version=1,
            to_version=2,
            lines=lines,
            summary={"added": 1, "removed": 1, "unchanged": 1},
        )
        assert result.added_count == 1
        assert result.removed_count == 1
        assert result.unchanged_count == 1


class TestDiffEngine:
    def test_create_engine(self):
        engine = DiffEngine()
        assert engine.context_lines == 3

    def test_create_engine_with_context(self):
        engine = DiffEngine(context_lines=5)
        assert engine.context_lines == 5

    def test_diff_identical_content(self):
        engine = DiffEngine()
        result = engine.diff("Hello World", "Hello World")
        assert result.has_changes is False
        assert result.added_count == 0
        assert result.removed_count == 0

    def test_diff_added_lines(self):
        engine = DiffEngine()
        result = engine.diff("Hello", "Hello\nWorld")
        assert result.has_changes is True
        assert result.added_count > 0

    def test_diff_removed_lines(self):
        engine = DiffEngine()
        result = engine.diff("Hello\nWorld", "Hello")
        assert result.has_changes is True
        assert result.removed_count > 0

    def test_diff_modified_lines(self):
        engine = DiffEngine()
        result = engine.diff("Hello World", "Hello Universe")
        assert result.has_changes is True

    def test_diff_empty_to_content(self):
        engine = DiffEngine()
        result = engine.diff("", "Hello World")
        assert result.has_changes is True
        assert result.added_count > 0

    def test_diff_content_to_empty(self):
        engine = DiffEngine()
        result = engine.diff("Hello World", "")
        assert result.has_changes is True
        assert result.removed_count > 0

    def test_diff_both_empty(self):
        engine = DiffEngine()
        result = engine.diff("", "")
        assert result.has_changes is False

    def test_diff_multiline(self):
        engine = DiffEngine()
        old = "line1\nline2\nline3\nline4"
        new = "line1\nmodified2\nline3\nline4\nline5"
        result = engine.diff(old, new)
        assert result.has_changes is True

    def test_diff_with_content_id(self):
        engine = DiffEngine()
        result = engine.diff("old", "new", content_id="doc-1", from_version=1, to_version=2)
        assert result.content_id == "doc-1"
        assert result.from_version == 1
        assert result.to_version == 2

    def test_diff_unicode_content(self):
        engine = DiffEngine()
        result = engine.diff("Hello 世界", "Hello 世界\n你好")
        assert result.has_changes is True

    def test_diff_whitespace_only_change(self):
        engine = DiffEngine()
        result = engine.diff("Hello", "Hello ")
        assert result.has_changes is True

    def test_diff_large_content(self):
        engine = DiffEngine()
        old = "\n".join(f"line {i}" for i in range(1000))
        new = "\n".join(f"line {i}" for i in range(1000)) + "\nline 1000"
        result = engine.diff(old, new)
        assert result.has_changes is True
        assert result.added_count >= 1

    def test_diff_get_unified_format(self):
        engine = DiffEngine()
        result = engine.diff("line1\nline2", "line1\nmodified2")
        unified = result.get_unified_format("old.txt", "new.txt")
        assert isinstance(unified, str)
        assert "---" in unified or "+++" in unified or "modified2" in unified

    def test_diff_get_stats(self):
        engine = DiffEngine()
        result = engine.diff("a\nb\nc", "a\nx\nc")
        stats = result.get_stats()
        assert isinstance(stats, dict)
        assert "added" in stats
        assert "removed" in stats
