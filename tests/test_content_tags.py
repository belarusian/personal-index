"""Tests for content_tags - tag management with autocomplete."""

from __future__ import annotations

import pytest

from personal_index.content_tags import (
    Tag,
    TagStore,
    TagAutocompleteResult,
)


class TestTagModel:
    """Tests for Tag dataclass."""

    def test_tag_creation_with_name_only(self):
        tag = Tag(name="python")
        assert tag.name == "python"
        assert tag.color == "#3498db"
        assert tag.description == ""
        assert tag.usage_count == 0

    def test_tag_creation_with_all_fields(self):
        tag = Tag(
            name="important",
            color="#ff0000",
            description="Important pages",
            usage_count=5,
        )
        assert tag.name == "important"
        assert tag.color == "#ff0000"
        assert tag.description == "Important pages"
        assert tag.usage_count == 5

    def test_tag_name_normalization(self):
        tag = Tag(name="  Python Tips  ")
        assert tag.name == "python tips"

    def test_tag_name_lowercase(self):
        tag = Tag(name="PYTHON")
        assert tag.name == "python"

    def test_tag_to_dict(self):
        tag = Tag(name="test", color="#ff0000", description="A test tag")
        d = tag.to_dict()
        assert d["name"] == "test"
        assert d["color"] == "#ff0000"
        assert d["description"] == "A test tag"

    def test_tag_from_dict(self):
        data = {
            "name": "test",
            "color": "#ff0000",
            "description": "A test tag",
            "usage_count": 3,
            "created_at": "2024-01-01T00:00:00",
        }
        tag = Tag.from_dict(data)
        assert tag.name == "test"
        assert tag.color == "#ff0000"
        assert tag.usage_count == 3

    def test_tag_equality(self):
        tag1 = Tag(name="python")
        tag2 = Tag(name="python")
        tag3 = Tag(name="rust")
        assert tag1 == tag2
        assert tag1 != tag3

    def test_tag_hash(self):
        tag1 = Tag(name="python")
        tag2 = Tag(name="python")
        assert hash(tag1) == hash(tag2)
        assert {tag1, tag2} == {tag1}

    def test_tag_repr(self):
        tag = Tag(name="python", color="#3776ab")
        assert "python" in repr(tag)
