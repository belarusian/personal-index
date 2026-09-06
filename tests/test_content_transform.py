"""Tests for content transform module."""


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
