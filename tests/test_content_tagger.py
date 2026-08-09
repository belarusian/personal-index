"""Tests for content_tagger module."""

import pytest
from personal_index.content_tagger.tag import Tag
from personal_index.content_tagger.detector import TopicDetector
from personal_index.content_tagger.tagger import ContentTagger


# ── Tag tests ──────────────────────────────────────────────

class TestTag:
    def test_create_tag(self):
        tag = Tag(name="python", confidence=0.95)
        assert tag.name == "python"
        assert tag.confidence == 0.95

    def test_tag_default_confidence(self):
        tag = Tag(name="testing")
        assert tag.confidence == 0.5

    def test_tag_to_dict(self):
        tag = Tag(name="ai", confidence=0.8)
        d = tag.to_dict()
        assert d == {"name": "ai", "confidence": 0.8}

    def test_tag_from_dict(self):
        tag = Tag.from_dict({"name": "ml", "confidence": 0.7})
        assert tag.name == "ml"
        assert tag.confidence == 0.7

    def test_tag_equality(self):
        t1 = Tag(name="web", confidence=0.9)
        t2 = Tag(name="web", confidence=0.9)
        assert t1 == t2

    def test_tag_inequality(self):
        t1 = Tag(name="web", confidence=0.9)
        t2 = Tag(name="mobile", confidence=0.9)
        assert t1 != t2

    def test_tag_sortable(self):
        tags = [Tag("b", 0.5), Tag("a", 0.9), Tag("c", 0.7)]
        sorted_tags = sorted(tags, key=lambda t: t.confidence, reverse=True)
        assert [t.name for t in sorted_tags] == ["a", "c", "b"]


# ── TopicDetector tests ────────────────────────────────────

class TestTopicDetector:
    def test_detect_single_topic(self):
        detector = TopicDetector()
        text = "Python is a great programming language for data science"
        tags = detector.detect(text)
        assert any(t.name == "programming" for t in tags)

    def test_detect_multiple_topics(self):
        detector = TopicDetector()
        text = "Machine learning and deep learning are transforming AI research"
        tags = detector.detect(text)
        names = [t.name for t in tags]
        assert "machine_learning" in names or "ai" in names

    def test_detect_no_topics(self):
        detector = TopicDetector()
        text = "asdf jklq zxcv"
        tags = detector.detect(text)
        assert len(tags) == 0

    def test_detect_empty_text(self):
        detector = TopicDetector()
        tags = detector.detect("")
        assert len(tags) == 0

    def test_detect_case_insensitive(self):
        detector = TopicDetector()
        text = "PYTHON Programming and DATA Science"
        tags = detector.detect(text)
        assert len(tags) > 0

    def test_detect_with_custom_topics(self):
        detector = TopicDetector()
        detector.add_topic("custom_topic", ["special_keyword", "unique_term"])
        text = "This contains special_keyword in it"
        tags = detector.detect(text)
        assert any(t.name == "custom_topic" for t in tags)

    def test_detect_confidence_based_on_matches(self):
        detector = TopicDetector()
        text = "Python Python Python programming programming"
        tags = detector.detect(text)
        python_tags = [t for t in tags if t.name == "programming"]
        if python_tags:
            assert python_tags[0].confidence > 0.5

    def test_detect_deduplicates_tags(self):
        detector = TopicDetector()
        text = "Python programming Python programming"
        tags = detector.detect(text)
        names = [t.name for t in tags]
        assert names.count("programming") <= 1

    def test_remove_topic(self):
        detector = TopicDetector()
        detector.add_topic("temp", ["tempword"])
        detector.remove_topic("temp")
        tags = detector.detect("tempword here")
        assert not any(t.name == "temp" for t in tags)

    def test_get_all_topics(self):
        detector = TopicDetector()
        topics = detector.get_all_topics()
        assert isinstance(topics, list)
        assert len(topics) > 0


# ── ContentTagger tests ────────────────────────────────────

class TestContentTagger:
    def test_tag_content(self):
        tagger = ContentTagger()
        result = tagger.tag("Python is great for web development and APIs")
        assert len(result.tags) > 0

    def test_tag_content_with_threshold(self):
        tagger = ContentTagger()
        result = tagger.tag("Python programming", min_confidence=0.99)
        assert all(t.confidence >= 0.99 for t in result.tags)

    def test_tag_empty_content(self):
        tagger = ContentTagger()
        result = tagger.tag("")
        assert len(result.tags) == 0

    def test_tag_result_to_dict(self):
        tagger = ContentTagger()
        result = tagger.tag("machine learning algorithms")
        d = result.to_dict()
        assert "tags" in d
        assert "content" in d

    def test_tag_result_from_dict(self):
        data = {"tags": [{"name": "test", "confidence": 0.8}], "content": "test content"}
        result = ContentTagger.TagResult.from_dict(data)
        assert len(result.tags) == 1
        assert result.tags[0].name == "test"

    def test_batch_tag(self):
        tagger = ContentTagger()
        items = ["Python code", "JavaScript framework", "Database query"]
        results = tagger.batch_tag(items)
        assert len(results) == 3

    def test_batch_tag_empty(self):
        tagger = ContentTagger()
        results = tagger.batch_tag([])
        assert len(results) == 0

    def test_get_tag_statistics(self):
        tagger = ContentTagger()
        tagger.tag("Python programming")
        tagger.tag("JavaScript development")
        stats = tagger.get_tag_statistics()
        assert isinstance(stats, dict)

    def test_add_custom_topic(self):
        tagger = ContentTagger()
        tagger.add_topic("mytopic", ["mykeyword"])
        result = tagger.tag("This has mykeyword")
        assert any(t.name == "mytopic" for t in result.tags)

    def test_clear_tags(self):
        tagger = ContentTagger()
        tagger.tag("some content")
        tagger.clear_statistics()
        stats = tagger.get_tag_statistics()
        assert stats == {}
