"""Tests for content transform module."""

from typing import Any

from personal_index.content_transform.normalizer import ContentNormalizer
from personal_index.content_transform.pipeline import TransformPipeline
from personal_index.content_transform.transformer import (
    ContentTransformer,
    create_field_add_transformer,
    create_field_filter_transformer,
    create_field_rename_transformer,
)


class TestContentTransformer:
    def test_transform_with_fn(self) -> None:
        t = ContentTransformer(
            name="test",
            transform_fn=lambda c: {**c, "added": True},
        )
        result = t.transform({"id": "1"})
        assert result["added"] is True

    def test_transform_no_fn(self) -> None:
        t = ContentTransformer(name="test")
        result = t.transform({"id": "1"})
        assert result == {"id": "1"}

    def test_transform_batch(self) -> None:
        t = ContentTransformer(
            name="test",
            transform_fn=lambda c: {**c, "x": 1},
        )
        items = [{"id": "1"}, {"id": "2"}]
        results = t.transform_batch(items)
        assert all(r["x"] == 1 for r in results)

    def test_rename_transformer(self) -> None:
        t = create_field_rename_transformer("old_field", "new_field")
        result = t.transform({"old_field": "value"})
        assert "new_field" in result
        assert "old_field" not in result

    def test_filter_transformer(self) -> None:
        t = create_field_filter_transformer(["id", "title"])
        result = t.transform({"id": "1", "title": "T", "extra": "x"})
        assert set(result.keys()) == {"id", "title"}

    def test_add_transformer(self) -> None:
        t = create_field_add_transformer("new_field", "value")
        result = t.transform({"id": "1"})
        assert result["new_field"] == "value"


class TestTransformPipeline:
    def test_single_transform(self) -> None:
        pipeline = TransformPipeline()
        pipeline.add(ContentTransformer(
            name="t1",
            transform_fn=lambda c: {**c, "a": 1},
        ))
        result = pipeline.transform({"id": "1"})
        assert result["a"] == 1

    def test_chained_transforms(self) -> None:
        pipeline = TransformPipeline()
        pipeline.add(ContentTransformer(
            name="t1",
            transform_fn=lambda c: {**c, "a": 1},
        )).add(ContentTransformer(
            name="t2",
            transform_fn=lambda c: {**c, "b": 2},
        ))
        result = pipeline.transform({"id": "1"})
        assert result["a"] == 1
        assert result["b"] == 2

    def test_pipeline_batch(self) -> None:
        pipeline = TransformPipeline()
        pipeline.add(ContentTransformer(
            name="t1",
            transform_fn=lambda c: {**c, "x": True},
        ))
        items = [{"id": "1"}, {"id": "2"}]
        results = pipeline.transform_batch(items)
        assert all(r["x"] for r in results)

    def test_clear(self) -> None:
        pipeline = TransformPipeline()
        pipeline.add(ContentTransformer(name="t1"))
        pipeline.clear()
        assert pipeline.step_count == 0

    def test_step_count(self) -> None:
        pipeline = TransformPipeline()
        pipeline.add(ContentTransformer(name="t1"))
        pipeline.add(ContentTransformer(name="t2"))
        assert pipeline.step_count == 2


class TestContentNormalizer:
    def test_normalize_title(self) -> None:
        n = ContentNormalizer()
        result = n.normalize({"title": "  hello world  "})
        assert result["title"] == "Hello World"

    def test_normalize_url(self) -> None:
        n = ContentNormalizer()
        result = n.normalize({"url": "example.com/path/"})
        assert result["url"] == "https://example.com/path"

    def test_normalize_tags(self) -> None:
        n = ContentNormalizer()
        result = n.normalize({"tags": ["Python", "Web Dev!"]})
        assert result["tags"] == ["python", "web-dev"]

    def test_normalize_batch(self) -> None:
        n = ContentNormalizer()
        items = [
            {"title": "hello", "tags": ["A"]},
            {"title": "world", "tags": ["B"]},
        ]
        results = n.normalize_batch(items)
        assert results[0]["title"] == "Hello"
        assert results[1]["title"] == "World"

    def test_normalize_disabled(self) -> None:
        n = ContentNormalizer(
            normalize_titles=False,
            normalize_urls=False,
            normalize_tags=False,
        )
        result = n.normalize({"title": "HELLO", "url": "x.com/", "tags": ["A"]})
        assert result["title"] == "HELLO"
        assert result["url"] == "x.com/"
        assert result["tags"] == ["A"]


class TestNormalizeUrlPinning:
    """Pinning tests for ContentNormalizer._normalize_url actual behavior."""

    def setup_method(self) -> None:
        self.n = ContentNormalizer()

    def test_bare_domain_gets_https_prefix(self) -> None:
        assert self.n._normalize_url("example.com") == "https://example.com"

    def test_trailing_slash_removed(self) -> None:
        assert self.n._normalize_url("https://example.com/") == "https://example.com"

    def test_http_prefix_not_doubled(self) -> None:
        assert self.n._normalize_url("http://example.com") == "http://example.com"

    def test_whitespace_stripped_before_prefix(self) -> None:
        assert self.n._normalize_url("  example.com  ") == "https://example.com"

    def test_lone_slash_becomes_https_colon(self) -> None:
        # The "https://" prefix is applied before the trailing-slash strip,
        # so "/" -> "https:///" -> rstrip("/") -> "https:". There is no
        # lone-slash exception.
        assert self.n._normalize_url("/") == "https:"

    def test_empty_stays_empty(self) -> None:
        assert self.n._normalize_url("") == ""


class TestNormalizeTagPinning:
    """Pinning tests for ContentNormalizer._normalize_tag actual behavior."""

    def setup_method(self) -> None:
        self.n = ContentNormalizer()

    def test_strip_lower_and_space_to_dash(self) -> None:
        assert self.n._normalize_tag("  My Tag  ") == "my-tag"

    def test_underscore_to_dash(self) -> None:
        assert self.n._normalize_tag("Hello_World") == "hello-world"

    def test_consecutive_dashes_collapsed(self) -> None:
        assert self.n._normalize_tag("a--b") == "a-b"

    def test_leading_dash_stripped(self) -> None:
        assert self.n._normalize_tag("-lead") == "lead"

    def test_trailing_dash_stripped(self) -> None:
        assert self.n._normalize_tag("trail-") == "trail"

    def test_dots_to_dashes(self) -> None:
        assert self.n._normalize_tag("a.b.c") == "a-b-c"

    def test_digits_preserved(self) -> None:
        assert self.n._normalize_tag("123") == "123"

    def test_empty_stays_empty(self) -> None:
        assert self.n._normalize_tag("") == ""


class TestNormalizeTitlePinning:
    """Pinning tests for ContentNormalizer._normalize_title actual behavior."""

    def setup_method(self) -> None:
        self.n = ContentNormalizer()

    def test_strip_and_title(self) -> None:
        assert self.n._normalize_title("  hello world  ") == "Hello World"

    def test_title_lowercases_rest(self) -> None:
        assert self.n._normalize_title("HELLO WORLD") == "Hello World"

    def test_each_word_capitalized(self) -> None:
        assert self.n._normalize_title("a b c") == "A B C"

    def test_non_alnum_boundary_splits_words(self) -> None:
        assert self.n._normalize_title("hello-world") == "Hello-World"

    def test_empty_stays_empty(self) -> None:
        assert self.n._normalize_title("") == ""


class TestNormalizePinning:
    """Pinning tests for ContentNormalizer.normalize actual behavior."""

    def setup_method(self) -> None:
        self.n = ContentNormalizer()

    def test_full_item_normalizes_title_url_tags(self) -> None:
        item = {
            "title": "  hello world  ",
            "url": "  https://X.com  ",
            "tags": [" A ", "b "],
        }
        result = self.n.normalize(item)
        assert result == {"title": "Hello World", "url": "https://X.com", "tags": ["a", "b"]}

    def test_normalize_is_non_destructive(self) -> None:
        item = {
            "title": "  hello world  ",
            "url": "  https://X.com  ",
            "tags": [" A ", "b "],
        }
        original = dict(item)
        self.n.normalize(item)
        assert item == original

    def test_absent_keys_pass_through(self) -> None:
        item = {"foo": "bar"}
        result = self.n.normalize(item)
        assert result == {"foo": "bar"}

    def test_non_list_tags_left_untouched(self) -> None:
        item = {"tags": "notalist"}
        result = self.n.normalize(item)
        assert result == {"tags": "notalist"}

    def test_flag_off_title_left_as_is(self) -> None:
        n = ContentNormalizer(normalize_titles=False)
        item = {"title": "  hello world  "}
        result = n.normalize(item)
        assert result == {"title": "  hello world  "}


class TestTransformerTransformPinning:
    def test_transform_fn_called_and_result_returned(self) -> None:
        calls: list[dict] = []

        def fn(c: dict) -> dict:
            calls.append(c)
            return {**c, "added": True}

        t = ContentTransformer(name="pin", transform_fn=fn)
        result = t.transform({"id": "1"})
        assert result == {"id": "1", "added": True}
        assert calls == [{"id": "1"}]

    def test_no_fn_returns_shallow_copy_not_same_object(self) -> None:
        t = ContentTransformer(name="pin")
        d = {"id": "1", "tags": ["a", "b"]}
        result = t.transform(d)
        assert result is not d
        assert result == d

    def test_input_not_mutated_with_fn(self) -> None:
        t = ContentTransformer(
            name="pin",
            transform_fn=lambda c: {**c, "added": True},
        )
        d = {"id": "1"}
        original = dict(d)
        t.transform(d)
        assert d == original

    def test_input_not_mutated_without_fn(self) -> None:
        t = ContentTransformer(name="pin")
        d = {"id": "1", "tags": ["a", "b"]}
        original = dict(d)
        result = t.transform(d)
        assert d == original
        # mutating the copy must not affect the input
        result["id"] = "changed"
        assert d["id"] == "1"


class TestCreateFieldAddTransformerPinning:
    """Pinning tests for create_field_add_transformer actual behavior."""

    def test_field_absent_is_added(self) -> None:
        t = create_field_add_transformer("new_field", "value")
        result = t.transform({"id": "1"})
        assert result == {"id": "1", "new_field": "value"}

    def test_field_present_is_overwritten(self) -> None:
        t = create_field_add_transformer("id", "OVERRIDDEN")
        result = t.transform({"id": "1", "tags": ["a"]})
        assert result == {"id": "OVERRIDDEN", "tags": ["a"]}

    def test_input_not_mutated(self) -> None:
        t = create_field_add_transformer("id", "X")
        d = {"id": "1", "tags": ["a"]}
        original = dict(d)
        result = t.transform(d)
        assert d == original
        # result is a new dict, not the input object
        assert result is not d
        # mutating the copy must not affect the input
        result["id"] = "changed"
        assert d["id"] == "1"

    def test_transformer_name_is_add_prefixed(self) -> None:
        t = create_field_add_transformer("new_field", "value")
        assert t.name == "add_new_field"


class TestCreateFieldRenameTransformerPinning:
    """Pinning tests for create_field_rename_transformer actual behavior."""

    def test_rename_when_old_name_present(self) -> None:
        t = create_field_rename_transformer("old", "new")
        result = t.transform({"old": "val", "x": 1})
        assert result == {"new": "val", "x": 1}
        assert "old" not in result

    def test_noop_when_old_name_absent(self) -> None:
        t = create_field_rename_transformer("old", "new")
        result = t.transform({"x": 1})
        assert result == {"x": 1}
        assert "new" not in result

    def test_input_not_mutated(self) -> None:
        t = create_field_rename_transformer("old", "new")
        d = {"old": "val", "x": 1}
        original = dict(d)
        result = t.transform(d)
        assert d == original
        assert result is not d
        # mutating the copy must not affect the input
        result["new"] = "changed"
        assert d["old"] == "val"

    def test_transformer_name_format(self) -> None:
        t = create_field_rename_transformer("foo", "bar")
        assert t.name == "rename_foo_to_bar"


class TestCreateFieldFilterTransformerPinning:
    """Pinning tests for create_field_filter_transformer actual behavior."""

    def test_keeps_only_listed_fields(self) -> None:
        t = create_field_filter_transformer(["a", "b"])
        result = t.transform({"a": 1, "b": 2, "c": 3})
        assert result == {"a": 1, "b": 2}
        assert "c" not in result

    def test_empty_dict_when_no_match(self) -> None:
        t = create_field_filter_transformer(["z"])
        result = t.transform({"a": 1, "b": 2})
        assert result == {}

    def test_empty_dict_when_fields_empty(self) -> None:
        t = create_field_filter_transformer([])
        result = t.transform({"a": 1})
        assert result == {}

    def test_input_not_mutated(self) -> None:
        t = create_field_filter_transformer(["a"])
        d = {"a": 1, "b": 2}
        original = dict(d)
        result = t.transform(d)
        assert d == original
        # result is a new dict, not the input object
        assert result is not d
        # mutating the copy must not affect the input
        result["a"] = "changed"
        assert d["a"] == 1

    def test_transformer_name_format(self) -> None:
        t = create_field_filter_transformer(["a", "b"])
        assert t.name == "filter_fields_2"

class TestTransformBatchPinning:
    """Pinning tests for ContentTransformer.transform_batch actual behavior."""

    def test_returns_new_list_and_input_not_mutated(self) -> None:
        t = create_field_add_transformer("k", "v")
        items = [{"a": 1}, {"b": 2}]
        original = [dict(d) for d in items]
        result = t.transform_batch(items)
        assert result is not items
        assert items == original

    def test_order_preserved_and_each_item_transformed(self) -> None:
        t = create_field_add_transformer("k", "v")
        items = [{"a": 1}, {"b": 2}, {"c": 3}]
        result = t.transform_batch(items)
        assert result == [{"a": 1, "k": "v"}, {"b": 2, "k": "v"}, {"c": 3, "k": "v"}]
        # each output item is a new dict, not the input item
        for out, inp in zip(result, items):
            assert out is not inp

    def test_empty_input_returns_empty_list(self) -> None:
        t = create_field_add_transformer("k", "v")
        result = t.transform_batch([])
        assert result == []
        assert isinstance(result, list)



class TestNormalizeBatchPinning:
    """Pinning tests for ContentNormalizer.normalize_batch actual behavior."""

    def test_returns_new_list_and_input_not_mutated(self) -> None:
        n = ContentNormalizer()
        items = [{"title": "  hello world  "}, {"url": "example.com"}]
        original = [dict(d) for d in items]
        result = n.normalize_batch(items)
        assert result is not items
        assert items == original

    def test_order_preserved_and_each_item_normalized(self) -> None:
        n = ContentNormalizer()
        items: list[dict[str, Any]] = [
            {"title": "  hello world  ", "url": "example.com", "tags": ["A B", "C"]},
            {"title": "X"},
        ]
        result = n.normalize_batch(items)
        assert result == [
            {"title": "Hello World", "url": "https://example.com", "tags": ["a-b", "c"]},
            {"title": "X"},
        ]
        # each output item is a new dict, not the input item
        for out, inp in zip(result, items):
            assert out is not inp

    def test_empty_input_returns_empty_list(self) -> None:
        n = ContentNormalizer()
        items: list[dict[str, Any]] = []
        result = n.normalize_batch(items)
        assert result == []
        assert isinstance(result, list)
