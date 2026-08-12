"""Tests for content merging module."""

from __future__ import annotations

from personal_index.content_merger import (
    ContentMerger,
    MergedContent,
    MergeSource,
)


def make_source(
    url: str = "https://example.com",
    title: str = "Test",
    content: str = "Content here",
    tags: list[str] | None = None,
    priority: int = 0,
    metadata: dict | None = None,
) -> MergeSource:
    return MergeSource(
        url=url,
        title=title,
        content=content,
        tags=tags or [],
        priority=priority,
        metadata=metadata or {},
    )


class TestMergeSource:
    def test_to_dict(self):
        source = make_source(tags=["python"], priority=5)
        d = source.to_dict()
        assert d["url"] == "https://example.com"
        assert d["tags"] == ["python"]
        assert d["priority"] == 5


class TestMergedContent:
    def test_to_dict(self):
        merged = MergedContent(
            url="https://x.com",
            title="Merged",
            content="Merged content",
            tags=["a", "b"],
            source_count=2,
            sources=["https://a.com", "https://b.com"],
        )
        d = merged.to_dict()
        assert d["source_count"] == 2
        assert d["merge_strategy"] == "concatenate"


class TestContentMerger:
    def test_merge_empty(self):
        merger = ContentMerger()
        assert merger.merge([]) is None

    def test_merge_single_source(self):
        merger = ContentMerger()
        source = make_source(content="Only content", tags=["python"])
        result = merger.merge([source])
        assert result is not None
        assert result.content == "Only content"
        assert result.source_count == 1

    def test_concatenate_strategy(self):
        merger = ContentMerger(strategy="concatenate")
        sources = [
            make_source(url="https://a.com", title="A", content="Content A", tags=["python"]),
            make_source(url="https://b.com", title="B", content="Content B", tags=["web"]),
        ]
        result = merger.merge(sources)
        assert "Content A" in result.content
        assert "Content B" in result.content
        assert "python" in result.tags
        assert "web" in result.tags
        assert result.source_count == 2

    def test_longest_strategy(self):
        merger = ContentMerger(strategy="longest")
        sources = [
            make_source(url="https://a.com", content="Short"),
            make_source(url="https://b.com", content="This is a much longer content that should be selected"),
        ]
        result = merger.merge(sources)
        assert result.content == "This is a much longer content that should be selected"
        assert result.merge_strategy == "longest"

    def test_highest_priority_strategy(self):
        merger = ContentMerger(strategy="highest_priority")
        sources = [
            make_source(url="https://a.com", content="Low priority", priority=1),
            make_source(url="https://b.com", content="High priority", priority=10),
        ]
        result = merger.merge(sources)
        assert result.content == "High priority"
        assert result.url == "https://b.com"

    def test_unique_paragraphs_strategy(self):
        merger = ContentMerger(strategy="unique_paragraphs")
        sources = [
            make_source(url="https://a.com", content="Para 1\n\nPara 2\n\nPara 3"),
            make_source(url="https://b.com", content="Para 2\n\nPara 4"),
        ]
        result = merger.merge(sources)
        assert "Para 1" in result.content
        assert "Para 2" in result.content
        assert "Para 3" in result.content
        assert "Para 4" in result.content
        # Para 2 should appear only once
        assert result.content.count("Para 2") == 1

    def test_tags_merged(self):
        merger = ContentMerger()
        sources = [
            make_source(tags=["python", "programming"]),
            make_source(tags=["python", "web"]),
        ]
        result = merger.merge(sources)
        assert set(result.tags) == {"python", "programming", "web"}

    def test_metadata_merged(self):
        merger = ContentMerger()
        sources = [
            make_source(metadata={"author": "Alice", "date": "2024-01-01"}),
            make_source(metadata={"author": "Bob", "lang": "en"}),
        ]
        result = merger.merge(sources)
        # Higher priority source wins for conflicts
        assert result.metadata["author"] == "Alice"
        assert result.metadata["lang"] == "en"

    def test_best_title(self):
        merger = ContentMerger()
        sources = [
            make_source(title=""),
            make_source(title="Short"),
            make_source(title="The Longest Title Here"),
        ]
        result = merger.merge(sources)
        assert result.title == "The Longest Title Here"

    def test_all_sources_tracked(self):
        merger = ContentMerger()
        sources = [
            make_source(url="https://a.com"),
            make_source(url="https://b.com"),
            make_source(url="https://c.com"),
        ]
        result = merger.merge(sources)
        assert len(result.sources) == 3
        assert "https://a.com" in result.sources
