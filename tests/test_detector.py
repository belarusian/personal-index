"""Tests for topic detection."""

from personal_index.content_tagger.detector import TopicDetector


class TestTopicDetector:
    def test_detect_programming(self):
        d = TopicDetector()
        tags = d.detect("This is about programming and code development")
        tag_names = [t.name for t in tags]
        assert "programming" in tag_names

    def test_detect_empty(self):
        d = TopicDetector()
        assert d.detect("") == []

    def test_detect_none_text(self):
        d = TopicDetector()
        assert d.detect(None) == []

    def test_detect_multiple_topics(self):
        d = TopicDetector()
        tags = d.detect("python programming docker kubernetes")
        tag_names = [t.name for t in tags]
        assert len(tag_names) >= 2

    def test_detect_sorted_by_confidence(self):
        d = TopicDetector()
        tags = d.detect("git github gitlab branch merge commit pull request rebase tag")
        if len(tags) >= 2:
            assert tags[0].confidence >= tags[1].confidence

    def test_add_topic(self):
        d = TopicDetector()
        d.add_topic("mytopic", ["mykeyword"])
        tags = d.detect("this has mykeyword in it")
        tag_names = [t.name for t in tags]
        assert "mytopic" in tag_names

    def test_remove_topic(self):
        d = TopicDetector()
        d.remove_topic("programming")
        tags = d.detect("programming code developer")
        tag_names = [t.name for t in tags]
        assert "programming" not in tag_names

    def test_get_all_topics(self):
        d = TopicDetector()
        topics = d.get_all_topics()
        assert "programming" in topics
        assert len(topics) >= 10

    def test_confidence_range(self):
        d = TopicDetector()
        tags = d.detect("python python python python python python")
        for tag in tags:
            assert 0.0 <= tag.confidence <= 1.0

    def test_default_topics_loaded(self):
        d = TopicDetector()
        topics = d.get_all_topics()
        expected = ["programming", "python", "web_development", "machine_learning", "ai"]
        for t in expected:
            assert t in topics
