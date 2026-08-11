"""Tests for the content transform module."""

from personal_index.content_transform import (
    TransformPipeline,
    add_domain,
    add_timestamp,
    add_word_count,
    create_standard_pipeline,
    enrich_with_defaults,
    filter_by_score,
    normalize_tags,
    normalize_title,
    normalize_url,
)


class TestTransformPipeline:
    def test_create(self) -> None:
        pipeline = TransformPipeline(name="test")
        assert pipeline.name == "test"
        assert len(pipeline.transforms) == 0

    def test_add_transform(self) -> None:
        pipeline = TransformPipeline()
        result = pipeline.add("test", lambda x: x)
        assert result is pipeline  # Chaining
        assert len(pipeline.transforms) == 1

    def test_apply(self) -> None:
        pipeline = TransformPipeline().add(
            "upper_title",
            lambda item: {**item, "title": item.get("title", "").upper()},
        )
        result = pipeline.apply({"title": "hello"})
        assert result["title"] == "HELLO"

    def test_apply_batch(self) -> None:
        pipeline = TransformPipeline().add(
            "add_key",
            lambda item: {**item, "processed": True},
        )
        items = [{"id": "1"}, {"id": "2"}]
        result = pipeline.apply_batch(items)
        assert all(item.get("processed") for item in result)

    def test_failed_transform_skipped(self) -> None:
        def failing(item):
            raise ValueError("fail")

        pipeline = TransformPipeline().add(
            "fail", failing,
        ).add(
            "add_key",
            lambda item: {**item, "ok": True},
        )
        result = pipeline.apply({"id": "1"})
        assert result.get("ok") is True


class TestBuiltInTransforms:
    def test_normalize_url_trailing_slash(self) -> None:
        item = {"url": "https://example.com/"}
        result = normalize_url(item)
        assert result["url"] == "https://example.com"

    def test_normalize_url_fragment(self) -> None:
        item = {"url": "https://example.com/page#section"}
        result = normalize_url(item)
        assert result["url"] == "https://example.com/page"

    def test_normalize_title(self) -> None:
        item = {"title": "  Hello World  "}
        result = normalize_title(item)
        assert result["title"] == "Hello World"

    def test_normalize_tags(self) -> None:
        item = {"tags": [" Python ", " WEB ", ""]}
        result = normalize_tags(item)
        assert result["tags"] == ["python", "web"]

    def test_add_domain(self) -> None:
        item = {"url": "https://example.com/path"}
        result = add_domain(item)
        assert result["domain"] == "example.com"

    def test_add_word_count(self) -> None:
        item = {"content": "Hello world this is a test"}
        result = add_word_count(item)
        assert result["word_count"] == 6

    def test_add_timestamp(self) -> None:
        item = {"id": "1"}
        result = add_timestamp(item)
        assert "processed_at" in result

    def test_filter_by_score(self) -> None:
        transform = filter_by_score(0.5)
        item = {"id": "1", "score": 0.3}
        result = transform(item)
        assert result.get("_filtered") is True

    def test_enrich_with_defaults(self) -> None:
        item = {"id": "1"}
        result = enrich_with_defaults(item)
        assert result["tags"] == []
        assert result["score"] == 0.0
        assert result["bookmarked"] is False


class TestStandardPipeline:
    def test_standard_pipeline(self) -> None:
        pipeline = create_standard_pipeline()
        assert len(pipeline.transforms) == 7

    def test_standard_pipeline_apply(self) -> None:
        pipeline = create_standard_pipeline()
        item = {
            "url": "https://example.com/",
            "title": "  Test  ",
            "tags": [" Python "],
            "content": "Hello world",
        }
        result = pipeline.apply(item)
        assert result["url"] == "https://example.com"
        assert result["title"] == "Test"
        assert result["tags"] == ["python"]
        assert result["domain"] == "example.com"
        assert result["word_count"] == 2
        assert "processed_at" in result
