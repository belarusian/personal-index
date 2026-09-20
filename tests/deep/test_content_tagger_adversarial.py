"""Adversarial tests for content_tagger module.

Tests boundary conditions, None/empty/unicode inputs, edge cases,
round-trips, and error handling for Tag, TopicDetector, and ContentTagger.
"""


from personal_index.content_tagger import ContentTagger, Tag, TopicDetector


class TestTagEdgeCases:
    """Tag dataclass edge cases."""

    def test_tag_empty_name(self):
        tag = Tag(name="", confidence=0.5)
        assert tag.name == ""
        assert tag.confidence == 0.5

    def test_tag_zero_confidence(self):
        tag = Tag(name="test", confidence=0.0)
        assert tag.confidence == 0.0

    def test_tag_confidence_above_one(self):
        tag = Tag(name="test", confidence=1.5)
        assert tag.confidence == 1.5

    def test_tag_negative_confidence(self):
        tag = Tag(name="test", confidence=-0.1)
        assert tag.confidence == -0.1

    def test_tag_unicode_name(self):
        tag = Tag(name="日本語", confidence=0.8)
        assert tag.name == "日本語"

    def test_tag_to_dict_roundtrip(self):
        tag = Tag(name="programming", confidence=0.75)
        data = tag.to_dict()
        restored = Tag.from_dict(data)
        assert restored == tag

    def test_tag_from_dict_missing_confidence(self):
        data = {"name": "test"}
        tag = Tag.from_dict(data)
        assert tag.name == "test"
        assert tag.confidence == 0.5

    def test_tag_equality_same_name_different_confidence(self):
        t1 = Tag(name="test", confidence=0.5)
        t2 = Tag(name="test", confidence=0.8)
        assert t1 != t2

    def test_tag_equality_different_name_same_confidence(self):
        t1 = Tag(name="test1", confidence=0.5)
        t2 = Tag(name="test2", confidence=0.5)
        assert t1 != t2

    def test_tag_equality_with_non_tag(self):
        tag = Tag(name="test", confidence=0.5)
        assert tag != "test"
        assert tag != {"name": "test"}


class TestTopicDetectorEdgeCases:
    """TopicDetector edge cases."""

    def test_detect_none_text(self):
        detector = TopicDetector()
        result = detector.detect("")
        assert result == []

    def test_detect_whitespace_only(self):
        detector = TopicDetector()
        result = detector.detect("   \t\n  ")
        assert result == []

    def test_detect_single_character(self):
        detector = TopicDetector()
        result = detector.detect("a")
        assert isinstance(result, list)

    def test_detect_unicode_text(self):
        detector = TopicDetector()
        result = detector.detect("Python プログラミング")
        assert isinstance(result, list)
        # Should detect python topic
        names = [t.name for t in result]
        assert "python" in names

    def test_detect_case_insensitive(self):
        detector = TopicDetector()
        result = detector.detect("PYTHON Programming")
        names = [t.name for t in result]
        assert "python" in names
        assert "programming" in names

    def test_detect_substring_matching(self):
        """Keyword 'ai' should match inside 'said'."""
        detector = TopicDetector()
        result = detector.detect("He said hello")
        names = [t.name for t in result]
        # 'ai' is a keyword for 'ai' topic, matches inside 'said'
        assert "ai" in names

    def test_detect_confidence_calculation(self):
        detector = TopicDetector()
        # One keyword match -> 0.5 + 0.1 = 0.6
        result = detector.detect("python")
        python_tag = [t for t in result if t.name == "python"][0]
        assert python_tag.confidence == 0.6

    def test_detect_confidence_cap_at_one(self):
        detector = TopicDetector()
        # Many matches should cap at 1.0
        text = "python python python python python python python python python python"
        result = detector.detect(text)
        python_tag = [t for t in result if t.name == "python"][0]
        assert python_tag.confidence == 1.0

    def test_detect_topic_emitted_once(self):
        detector = TopicDetector()
        # Multiple keywords from same topic should emit topic once
        result = detector.detect("python django flask")
        python_tags = [t for t in result if t.name == "python"]
        assert len(python_tags) == 1

    def test_detect_results_sorted_by_confidence(self):
        detector = TopicDetector()
        result = detector.detect("python programming code")
        confidences = [t.confidence for t in result]
        assert confidences == sorted(confidences, reverse=True)

    def test_add_topic_custom(self):
        detector = TopicDetector()
        detector.add_topic("custom_topic", ["custom_keyword"])
        result = detector.detect("custom_keyword")
        names = [t.name for t in result]
        assert "custom_topic" in names

    def test_add_topic_overwrites_existing(self):
        detector = TopicDetector()
        detector.add_topic("python", ["different_keyword"])
        result = detector.detect("different_keyword")
        names = [t.name for t in result]
        assert "python" in names

    def test_remove_topic(self):
        detector = TopicDetector()
        detector.remove_topic("python")
        result = detector.detect("python")
        names = [t.name for t in result]
        assert "python" not in names

    def test_remove_nonexistent_topic(self):
        detector = TopicDetector()
        detector.remove_topic("nonexistent")
        # Should not raise

    def test_get_all_topics(self):
        detector = TopicDetector()
        topics = detector.get_all_topics()
        assert "python" in topics
        assert "programming" in topics

    def test_detect_special_regex_characters(self):
        """Keywords with regex special chars should be escaped."""
        detector = TopicDetector()
        detector.add_topic("regex_test", ["test.com", "a+b", "x*y"])
        result = detector.detect("visit test.com or a+b")
        names = [t.name for t in result]
        assert "regex_test" in names

    def test_detect_empty_keyword_list(self):
        detector = TopicDetector()
        detector.add_topic("empty_keywords", [])
        result = detector.detect("anything")
        names = [t.name for t in result]
        assert "empty_keywords" not in names

    def test_detect_duplicate_keywords_in_topic(self):
        detector = TopicDetector()
        detector.add_topic("dup_test", ["word", "word"])
        result = detector.detect("word")
        # Should count both occurrences
        tag = [t for t in result if t.name == "dup_test"][0]
        assert tag.confidence == 0.7  # 0.5 + 2*0.1


class TestContentTaggerEdgeCases:
    """ContentTagger edge cases."""

    def test_tag_empty_content(self):
        tagger = ContentTagger()
        result = tagger.tag("")
        assert result.tags == []
        assert result.content == ""

    def test_tag_whitespace_content(self):
        tagger = ContentTagger()
        result = tagger.tag("   ")
        assert result.tags == []

    def test_tag_min_confidence_filtering(self):
        tagger = ContentTagger()
        # Low confidence tags should be filtered
        result = tagger.tag("python", min_confidence=0.9)
        # python has one keyword match -> 0.6 confidence, filtered out
        assert all(t.confidence >= 0.9 for t in result.tags)

    def test_tag_min_confidence_zero(self):
        tagger = ContentTagger()
        result = tagger.tag("python", min_confidence=0.0)
        assert any(t.name == "python" for t in result.tags)

    def test_batch_tag_empty_list(self):
        tagger = ContentTagger()
        results = tagger.batch_tag([])
        assert results == []

    def test_batch_tag_mixed_content(self):
        tagger = ContentTagger()
        results = tagger.batch_tag(["python code", "", "   ", "html css"])
        assert len(results) == 4
        assert results[0].tags != []
        assert results[1].tags == []
        assert results[2].tags == []
        assert results[3].tags != []

    def test_tag_statistics_tracking(self):
        tagger = ContentTagger()
        tagger.tag("python")
        tagger.tag("python")
        tagger.tag("docker")
        stats = tagger.get_tag_statistics()
        assert stats.get("python", 0) == 2
        assert stats.get("devops", 0) == 1

    def test_tag_statistics_returns_copy(self):
        tagger = ContentTagger()
        tagger.tag("python")
        stats1 = tagger.get_tag_statistics()
        stats1["fake"] = 999
        stats2 = tagger.get_tag_statistics()
        assert "fake" not in stats2

    def test_clear_statistics(self):
        tagger = ContentTagger()
        tagger.tag("python")
        tagger.clear_statistics()
        stats = tagger.get_tag_statistics()
        assert stats == {}

    def test_add_topic_propagates_to_detector(self):
        tagger = ContentTagger()
        tagger.add_topic("my_topic", ["my_keyword"])
        result = tagger.tag("my_keyword")
        names = [t.name for t in result.tags]
        assert "my_topic" in names

    def test_tag_result_to_dict_roundtrip(self):
        from personal_index.content_tagger.tagger import TagResult
        tagger = ContentTagger()
        result = tagger.tag("python")
        data = result.to_dict()
        restored = TagResult.from_dict(data)
        assert restored.content == result.content
        assert len(restored.tags) == len(result.tags)

    def test_tag_result_from_dict_empty_tags(self):
        from personal_index.content_tagger.tagger import TagResult
        data = {"content": "test", "tags": []}
        result = TagResult.from_dict(data)
        assert result.tags == []

    def test_tag_result_from_dict_missing_tags(self):
        from personal_index.content_tagger.tagger import TagResult
        data = {"content": "test"}
        result = TagResult.from_dict(data)
        assert result.tags == []

    def test_tag_unicode_content(self):
        tagger = ContentTagger()
        result = tagger.tag("Python プログラミングでコードを書く")
        assert isinstance(result.tags, list)

    def test_tag_very_long_content(self):
        tagger = ContentTagger()
        long_text = "python " * 10000
        result = tagger.tag(long_text)
        assert any(t.name == "python" for t in result.tags)

    def test_tag_multiple_topics_same_content(self):
        tagger = ContentTagger()
        result = tagger.tag("python programming web development html css")
        names = [t.name for t in result.tags]
        assert "python" in names
        assert "programming" in names
        assert "web_development" in names


class TestIntegrationEdgeCases:
    """Integration-level edge cases."""

    def test_full_roundtrip_with_custom_topic(self):
        tagger = ContentTagger()
        tagger.add_topic("my_custom", ["custom_word"])
        result = tagger.tag("custom_word here")
        data = result.to_dict()
        from personal_index.content_tagger.tagger import TagResult
        restored = TagResult.from_dict(data)
        names = [t.name for t in restored.tags]
        assert "my_custom" in names

    def test_detector_and_tagger_independent(self):
        detector = TopicDetector()
        tagger = ContentTagger()
        detector.add_topic("detector_only", ["det_word"])
        tagger.add_topic("tagger_only", ["tag_word"])

        det_result = detector.detect("det_word")
        tag_result = tagger.tag("det_word")
        assert any(t.name == "detector_only" for t in det_result)
        assert not any(t.name == "detector_only" for t in tag_result.tags)

    def test_idempotent_tagging(self):
        tagger = ContentTagger()
        result1 = tagger.tag("python code")
        result2 = tagger.tag("python code")
        assert len(result1.tags) == len(result2.tags)
        for t1, t2 in zip(result1.tags, result2.tags):
            assert t1.name == t2.name
            assert t1.confidence == t2.confidence
