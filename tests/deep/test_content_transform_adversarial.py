"""Adversarial deep tests for content_transform module.

Tests the ContentTransformer class and factory functions with edge cases:
- None/empty inputs
- Unicode keys and values
- Input mutation (shallow copy guarantees)
- Batch operations
- Field rename edge cases
- Field filter edge cases
"""

from personal_index.content_transform.transformer import (
    ContentTransformer,
    create_field_rename_transformer,
    create_field_filter_transformer,
)


class TestContentTransformerTransform:
    """Tests for ContentTransformer.transform()."""

    def test_transform_with_none_fn_returns_shallow_copy(self):
        """transform() with no transform_fn returns a shallow copy."""
        t = ContentTransformer()
        original = {"title": "Test", "body": "Content"}
        result = t.transform(original)
        assert result == original
        assert result is not original  # shallow copy, not same object

    def test_transform_with_custom_fn(self):
        """transform() calls the custom transform_fn."""
        def upper_title(content):
            result = dict(content)
            result["title"] = result["title"].upper()
            return result

        t = ContentTransformer(name="upper", transform_fn=upper_title)
        original = {"title": "hello", "body": "world"}
        result = t.transform(original)
        assert result["title"] == "HELLO"
        assert result["body"] == "world"

    def test_transform_empty_dict(self):
        """transform() handles empty dict."""
        t = ContentTransformer()
        result = t.transform({})
        assert result == {}
        assert isinstance(result, dict)

    def test_transform_unicode_keys_and_values(self):
        """transform() handles unicode keys and values."""
        t = ContentTransformer()
        original = {"título": "Café", "日本語": "テスト"}
        result = t.transform(original)
        assert result["título"] == "Café"
        assert result["日本語"] == "テスト"

    def test_transform_nested_dict_shallow_copy(self):
        """transform() shallow copy: nested objects shared."""
        t = ContentTransformer()
        nested = {"inner": {"value": 42}}
        original = {"data": nested}
        result = t.transform(original)
        assert result["data"] is nested  # shallow: nested object is same

    def test_transform_none_values(self):
        """transform() handles None values."""
        t = ContentTransformer()
        original = {"key": None, "other": "value"}
        result = t.transform(original)
        assert result["key"] is None
        assert result["other"] == "value"


class TestContentTransformerTransformBatch:
    """Tests for ContentTransformer.transform_batch()."""

    def test_transform_batch_empty_list(self):
        """transform_batch() with empty list returns empty list."""
        t = ContentTransformer()
        result = t.transform_batch([])
        assert result == []
        assert isinstance(result, list)

    def test_transform_batch_single_item(self):
        """transform_batch() with single item."""
        t = ContentTransformer()
        items = [{"title": "One"}]
        result = t.transform_batch(items)
        assert len(result) == 1
        assert result[0]["title"] == "One"

    def test_transform_batch_multiple_items(self):
        """transform_batch() with multiple items."""
        t = ContentTransformer()
        items = [{"title": "One"}, {"title": "Two"}, {"title": "Three"}]
        result = t.transform_batch(items)
        assert len(result) == 3
        assert result[0]["title"] == "One"
        assert result[1]["title"] == "Two"
        assert result[2]["title"] == "Three"

    def test_transform_batch_returns_new_list(self):
        """transform_batch() returns a new list, not the input."""
        t = ContentTransformer()
        items = [{"title": "One"}]
        result = t.transform_batch(items)
        assert result is not items

    def test_transform_batch_preserves_order(self):
        """transform_batch() preserves item order."""
        def add_index(content):
            result = dict(content)
            result["index"] = content["index"]
            return result

        t = ContentTransformer(name="index", transform_fn=add_index)
        items = [
            {"index": 3, "title": "C"},
            {"index": 1, "title": "A"},
            {"index": 2, "title": "B"},
        ]
        result = t.transform_batch(items)
        assert result[0]["index"] == 3
        assert result[1]["index"] == 1
        assert result[2]["index"] == 2

    def test_transform_batch_with_custom_fn(self):
        """transform_batch() applies custom transform_fn to each item."""
        def double_value(content):
            result = dict(content)
            result["value"] = content["value"] * 2
            return result

        t = ContentTransformer(name="double", transform_fn=double_value)
        items = [{"value": 1}, {"value": 2}, {"value": 3}]
        result = t.transform_batch(items)
        assert result[0]["value"] == 2
        assert result[1]["value"] == 4
        assert result[2]["value"] == 6


class TestCreateFieldRenameTransformer:
    """Tests for create_field_rename_transformer()."""

    def test_rename_field_present(self):
        """Rename when old field is present."""
        t = create_field_rename_transformer("old", "new")
        original = {"old": "value", "other": "kept"}
        result = t.transform(original)
        assert "new" in result
        assert result["new"] == "value"
        assert "old" not in result
        assert result["other"] == "kept"

    def test_rename_field_absent(self):
        """Rename when old field is absent (no-op)."""
        t = create_field_rename_transformer("missing", "new")
        original = {"other": "kept"}
        result = t.transform(original)
        assert "new" not in result
        assert result == original

    def test_rename_old_equals_new(self):
        """Rename where old and new names are the same."""
        t = create_field_rename_transformer("same", "same")
        original = {"same": "value"}
        result = t.transform(original)
        assert result["same"] == "value"

    def test_rename_returns_new_dict(self):
        """Rename returns a new dict, input not mutated."""
        t = create_field_rename_transformer("old", "new")
        original = {"old": "value"}
        result = t.transform(original)
        assert result is not original
        assert "old" in original  # input not mutated

    def test_rename_unicode_field_names(self):
        """Rename with unicode field names."""
        t = create_field_rename_transformer("título", "title")
        original = {"título": "Café"}
        result = t.transform(original)
        assert result["title"] == "Café"
        assert "título" not in result

    def test_rename_empty_dict(self):
        """Rename on empty dict."""
        t = create_field_rename_transformer("old", "new")
        result = t.transform({})
        assert result == {}

    def test_rename_overwrites_existing_new_field(self):
        """Rename overwrites if new field already exists."""
        t = create_field_rename_transformer("old", "new")
        original = {"old": "from_old", "new": "existing"}
        result = t.transform(original)
        assert result["new"] == "from_old"


class TestCreateFieldFilterTransformer:
    """Tests for create_field_filter_transformer()."""

    def test_filter_keeps_specified_fields(self):
        """Filter keeps only specified fields."""
        t = create_field_filter_transformer(["title", "body"])
        original = {"title": "T", "body": "B", "extra": "E"}
        result = t.transform(original)
        assert "title" in result
        assert "body" in result
        assert "extra" not in result

    def test_filter_empty_fields_list(self):
        """Filter with empty fields list returns empty dict."""
        t = create_field_filter_transformer([])
        original = {"title": "T", "body": "B"}
        result = t.transform(original)
        assert result == {}

    def test_filter_all_fields_missing(self):
        """Filter where none of the specified fields exist."""
        t = create_field_filter_transformer(["missing1", "missing2"])
        original = {"title": "T"}
        result = t.transform(original)
        assert result == {}

    def test_filter_returns_new_dict(self):
        """Filter returns a new dict, input not mutated."""
        t = create_field_filter_transformer(["title"])
        original = {"title": "T", "body": "B"}
        result = t.transform(original)
        assert result is not original
        assert "body" in original  # input not mutated

    def test_filter_preserves_key_order(self):
        """Filter preserves the original key order."""
        t = create_field_filter_transformer(["c", "a"])
        original = {"a": 1, "b": 2, "c": 3}
        result = t.transform(original)
        assert list(result.keys()) == ["a", "c"]  # original order

    def test_filter_unicode_fields(self):
        """Filter with unicode field names."""
        t = create_field_filter_transformer(["título"])
        original = {"título": "Café", "body": "B"}
        result = t.transform(original)
        assert result == {"título": "Café"}

    def test_filter_empty_dict(self):
        """Filter on empty dict."""
        t = create_field_filter_transformer(["title"])
        result = t.transform({})
        assert result == {}


class TestTransformerName:
    """Tests for transformer naming."""

    def test_default_name(self):
        """Default transformer name."""
        t = ContentTransformer()
        assert t.name == "default"

    def test_rename_transformer_name(self):
        """Rename transformer has correct name."""
        t = create_field_rename_transformer("old", "new")
        assert t.name == "rename_old_to_new"

    def test_filter_transformer_name(self):
        """Filter transformer has correct name."""
        t = create_field_filter_transformer(["a", "b", "c"])
        assert t.name == "filter_fields_3"

    def test_filter_transformer_name_empty(self):
        """Filter transformer name with empty fields."""
        t = create_field_filter_transformer([])
        assert t.name == "filter_fields_0"
