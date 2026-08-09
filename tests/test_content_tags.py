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


class TestTagStoreCRUD:
    """Tests for TagStore CRUD operations."""

    def setup_method(self):
        self.store = TagStore()

    def test_create_tag(self):
        tag = self.store.create_tag("python")
        assert tag.name == "python"
        assert tag.color == "#3498db"

    def test_create_tag_with_color(self):
        tag = self.store.create_tag("python", color="#3776ab")
        assert tag.color == "#3776ab"

    def test_create_tag_with_description(self):
        tag = self.store.create_tag("python", description="Python programming")
        assert tag.description == "Python programming"

    def test_get_existing_tag(self):
        self.store.create_tag("python")
        tag = self.store.get_tag("python")
        assert tag is not None
        assert tag.name == "python"

    def test_get_nonexistent_tag(self):
        assert self.store.get_tag("nonexistent") is None

    def test_get_tag_case_insensitive(self):
        self.store.create_tag("python")
        tag = self.store.get_tag("PYTHON")
        assert tag is not None
        assert tag.name == "python"

    def test_list_tags_empty(self):
        assert self.store.list_tags() == []

    def test_list_tags_sorted_by_name(self):
        self.store.create_tag("zebra")
        self.store.create_tag("apple")
        self.store.create_tag("mango")
        tags = self.store.list_tags()
        assert [t.name for t in tags] == ["apple", "mango", "zebra"]

    def test_list_tags_sorted_by_usage(self):
        self.store.create_tag("a")
        self.store.create_tag("b")
        self.store.create_tag("c")
        self.store._tags["b"].usage_count = 10
        self.store._tags["a"].usage_count = 5
        tags = self.store.list_tags(sort_by="usage_count")
        assert [t.name for t in tags] == ["b", "a", "c"]

    def test_delete_existing_tag(self):
        self.store.create_tag("python")
        assert self.store.delete_tag("python") is True
        assert self.store.get_tag("python") is None

    def test_delete_nonexistent_tag(self):
        assert self.store.delete_tag("nonexistent") is False

    def test_delete_tag_removes_from_content(self):
        self.store.create_tag("python")
        self.store.add_tag_to_content("content1", "python")
        self.store.delete_tag("python")
        assert self.store.get_tags_for_content("content1") == []

    def test_tag_count(self):
        assert self.store.get_tag_count() == 0
        self.store.create_tag("a")
        assert self.store.get_tag_count() == 1
        self.store.create_tag("b")
        assert self.store.get_tag_count() == 2

    def test_clear(self):
        self.store.create_tag("a")
        self.store.create_tag("b")
        self.store.add_tag_to_content("c1", "a")
        self.store.clear()
        assert self.store.get_tag_count() == 0
        assert self.store.get_tagged_content_count() == 0


class TestTagStoreContentAssociation:
    """Tests for TagStore content-tag associations."""

    def setup_method(self):
        self.store = TagStore()
        self.store.create_tag("python")
        self.store.create_tag("web")
        self.store.create_tag("devops")

    def test_add_tag_to_content(self):
        result = self.store.add_tag_to_content("page1", "python")
        assert result is True

    def test_add_nonexistent_tag_to_content(self):
        result = self.store.add_tag_to_content("page1", "nonexistent")
        assert result is False

    def test_get_tags_for_content(self):
        self.store.add_tag_to_content("page1", "python")
        self.store.add_tag_to_content("page1", "web")
        tags = self.store.get_tags_for_content("page1")
        names = sorted([t.name for t in tags])
        assert names == ["python", "web"]

    def test_get_tags_for_untagged_content(self):
        tags = self.store.get_tags_for_content("untagged")
        assert tags == []

    def test_remove_tag_from_content(self):
        self.store.add_tag_to_content("page1", "python")
        result = self.store.remove_tag_from_content("page1", "python")
        assert result is True
        assert self.store.get_tags_for_content("page1") == []

    def test_remove_nonexistent_tag_from_content(self):
        result = self.store.remove_tag_from_content("page1", "python")
        assert result is False

    def test_remove_tag_from_untagged_content(self):
        result = self.store.remove_tag_from_content("page1", "python")
        assert result is False

    def test_get_content_for_tag(self):
        self.store.add_tag_to_content("page1", "python")
        self.store.add_tag_to_content("page2", "python")
        content = self.store.get_content_for_tag("python")
        assert set(content) == {"page1", "page2"}

    def test_get_content_for_tag_empty(self):
        content = self.store.get_content_for_tag("devops")
        assert content == []

    def test_usage_count_increments(self):
        assert self.store.get_tag("python").usage_count == 0
        self.store.add_tag_to_content("page1", "python")
        assert self.store.get_tag("python").usage_count == 1
        self.store.add_tag_to_content("page2", "python")
        assert self.store.get_tag("python").usage_count == 2

    def test_usage_count_decrements_on_remove(self):
        self.store.add_tag_to_content("page1", "python")
        assert self.store.get_tag("python").usage_count == 1
        self.store.remove_tag_from_content("page1", "python")
        assert self.store.get_tag("python").usage_count == 0

    def test_tagged_content_count(self):
        assert self.store.get_tagged_content_count() == 0
        self.store.add_tag_to_content("page1", "python")
        assert self.store.get_tagged_content_count() == 1
        self.store.add_tag_to_content("page1", "web")
        assert self.store.get_tagged_content_count() == 1
        self.store.add_tag_to_content("page2", "web")
        assert self.store.get_tagged_content_count() == 2


class TestTagStoreAutocomplete:
    """Tests for TagStore autocomplete feature."""

    def setup_method(self):
        self.store = TagStore()
        self.store.create_tag("python")
        self.store.create_tag("python-web")
        self.store.create_tag("python-data")
        self.store.create_tag("javascript")
        self.store.create_tag("java")
        self.store.create_tag("rust")
        self.store._tags["python"].usage_count = 10
        self.store._tags["javascript"].usage_count = 5

    def test_autocomplete_empty_query_returns_popular(self):
        result = self.store.autocomplete("")
        assert "python" in result.popular_tags
        assert result.exact_match is None

    def test_autocomplete_exact_match(self):
        result = self.store.autocomplete("python")
        assert result.exact_match == "python"
        assert "python" in result.suggestions

    def test_autocomplete_partial_match(self):
        result = self.store.autocomplete("pyt")
        assert "python" in result.partial_matches
        assert "python-web" in result.partial_matches

    def test_autocomplete_no_match(self):
        result = self.store.autocomplete("xyz")
        assert result.exact_match is None
        assert result.partial_matches == []
        assert result.suggestions == []

    def test_autocomplete_limit(self):
        result = self.store.autocomplete("", limit=2)
        assert len(result.popular_tags) <= 2

    def test_autocomplete_case_insensitive(self):
        result = self.store.autocomplete("PYTHON")
        assert result.exact_match == "python"

    def test_autocomplete_result_to_dict(self):
        result = self.store.autocomplete("python")
        d = result.to_dict()
        assert "suggestions" in d
        assert "exact_match" in d
        assert "partial_matches" in d
        assert "popular_tags" in d


class TestTagStoreMergeRename:
    """Tests for TagStore merge and rename operations."""

    def setup_method(self):
        self.store = TagStore()
        self.store.create_tag("python")
        self.store.create_tag("py")
        self.store.create_tag("web")
        self.store.add_tag_to_content("page1", "python")
        self.store.add_tag_to_content("page2", "python")
        self.store.add_tag_to_content("page1", "py")

    def test_rename_tag(self):
        result = self.store.rename_tag("py", "python3")
        assert result is True
        assert self.store.get_tag("py") is None
        assert self.store.get_tag("python3") is not None

    def test_rename_nonexistent_tag(self):
        result = self.store.rename_tag("nonexistent", "new")
        assert result is False

    def test_rename_to_existing_merges(self):
        result = self.store.rename_tag("py", "python")
        assert result is True
        assert self.store.get_tag("py") is None
        content = self.store.get_content_for_tag("python")
        assert set(content) == {"page1", "page2"}

    def test_merge_tags(self):
        result = self.store.merge_tags("py", "python")
        assert result is True
        assert self.store.get_tag("py") is None
        content = self.store.get_content_for_tag("python")
        assert set(content) == {"page1", "page2"}

    def test_merge_nonexistent_source(self):
        result = self.store.merge_tags("nonexistent", "python")
        assert result is False

    def test_merge_creates_target_if_needed(self):
        result = self.store.merge_tags("py", "newtag")
        assert result is True
        assert self.store.get_tag("newtag") is not None

    def test_merge_preserves_usage_count(self):
        self.store._tags["py"].usage_count = 3
        self.store._tags["python"].usage_count = 2
        self.store.merge_tags("py", "python")
        assert self.store.get_tag("python").usage_count == 5

    def test_get_stats(self):
        stats = self.store.get_stats()
        assert stats["total_tags"] == 3
        assert stats["tagged_content"] == 2
        assert len(stats["most_used"]) > 0
