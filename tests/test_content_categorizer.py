"""Tests for personal_index.content_categorizer module.

Covers:
- categorize_content() helper
- get_builtin_topics()
- load_custom_topics() / save_custom_topics()
- Topic dataclass
- TopicScore dataclass
- ContentCategorizer class methods
"""

from __future__ import annotations

import pytest

from personal_index.content_categorizer import (
    BUILTIN_TOPICS,
    CategorizationResult,
    ContentCategorizer,
    TopicCategory,
    TopicScore,
)

# ---------------------------------------------------------------------------
# TopicCategory dataclass tests
# ---------------------------------------------------------------------------


class TestTopicCategory:
    """Tests for the TopicCategory dataclass."""

    def test_topic_defaults(self):
        """Topic defaults: name required, keywords=[], weight=1.0, enabled=True."""
        topic = TopicCategory(name="test")
        assert topic.name == "test"
        assert topic.keywords == []
        assert topic.weight == 1.0
        assert topic.description == ""

    def test_topic_custom_values(self):
        """Topic with custom values."""
        topic = TopicCategory(
            name="science",
            keywords=["quantum", "physics"],
            description="Science topics",
            weight=2.0,
        )
        assert topic.name == "science"
        assert topic.keywords == ["quantum", "physics"]
        assert topic.description == "Science topics"
        assert topic.weight == 2.0

    def test_topic_keyword_normalization(self):
        """Keywords are normalized to lowercase in __post_init__."""
        topic = TopicCategory(name="test", keywords=["UPPER", "MiXeD"])
        assert "upper" in topic.keywords
        assert "mixed" in topic.keywords


# ---------------------------------------------------------------------------
# TopicScore dataclass tests
# ---------------------------------------------------------------------------


class TestTopicScore:
    """Tests for the TopicScore dataclass."""

    def test_topic_score_fields(self):
        """TopicScore has topic, score, matched_keywords, signal_sources."""
        ts = TopicScore(
            topic="technology",
            score=0.85,
            matched_keywords=["api", "code"],
            signal_sources=["text", "title"],
        )
        assert ts.topic == "technology"
        assert ts.score == 0.85
        assert ts.matched_keywords == ["api", "code"]
        assert ts.signal_sources == ["text", "title"]

    def test_topic_score_defaults(self):
        """TopicScore defaults: matched_keywords=[], signal_sources=[]."""
        ts = TopicScore(topic="test", score=0.0)
        assert ts.matched_keywords == []
        assert ts.signal_sources == []

    def test_topic_score_comparison(self):
        """TopicScore supports > and < comparison by score."""
        ts1 = TopicScore(topic="a", score=0.5)
        ts2 = TopicScore(topic="b", score=0.8)
        assert ts2 > ts1
        assert ts1 < ts2

    def test_topic_score_equal(self):
        """TopicScore equal scores."""
        ts1 = TopicScore(topic="a", score=0.5)
        ts2 = TopicScore(topic="b", score=0.5)
        assert not (ts1 > ts2)
        assert not (ts2 > ts1)


# ---------------------------------------------------------------------------
# CategorizationResult tests
# ---------------------------------------------------------------------------


class TestCategorizationResult:
    """Tests for CategorizationResult dataclass."""

    def test_result_creation(self):
        result = CategorizationResult(
            primary_topic="technology",
            topics=[TopicScore(topic="technology", score=0.9)],
            confidence=0.9,
        )
        assert result.primary_topic == "technology"
        assert result.confidence == 0.9

    def test_secondary_topics(self):
        result = CategorizationResult(
            primary_topic="tech",
            topics=[
                TopicScore(topic="tech", score=0.9),
                TopicScore(topic="science", score=0.5),
            ],
        )
        assert len(result.secondary_topics) == 1
        assert result.secondary_topics[0].topic == "science"

    def test_top_n(self):
        result = CategorizationResult(
            primary_topic="tech",
            topics=[
                TopicScore(topic="tech", score=0.9),
                TopicScore(topic="science", score=0.5),
                TopicScore(topic="business", score=0.3),
            ],
        )
        top2 = result.top_n(2)
        assert len(top2) == 2
        assert top2[0].topic == "tech"

    def test_top_n_default_is_three(self):
        result = CategorizationResult(
            primary_topic="tech",
            topics=[
                TopicScore(topic="a", score=0.9),
                TopicScore(topic="b", score=0.5),
                TopicScore(topic="c", score=0.3),
                TopicScore(topic="d", score=0.1),
            ],
        )
        top = result.top_n()
        assert [t.topic for t in top] == ["a", "b", "c"]

    def test_top_n_returns_new_list_not_internal(self):
        topics = [
            TopicScore(topic="a", score=0.9),
            TopicScore(topic="b", score=0.5),
        ]
        result = CategorizationResult(primary_topic="a", topics=topics)
        top = result.top_n()
        assert top is not result.topics
        assert top is not topics
        # mutating the returned list does not affect the internal list
        top.append(TopicScore(topic="z", score=0.0))
        assert len(result.topics) == 2

    def test_top_n_zero_returns_empty(self):
        result = CategorizationResult(
            primary_topic="a",
            topics=[TopicScore(topic="a", score=0.9)],
        )
        assert result.top_n(0) == []

    def test_top_n_larger_than_len_returns_all(self):
        result = CategorizationResult(
            primary_topic="a",
            topics=[
                TopicScore(topic="a", score=0.9),
                TopicScore(topic="b", score=0.5),
            ],
        )
        top = result.top_n(10)
        assert [t.topic for t in top] == ["a", "b"]

    def test_top_n_preserves_order_and_no_mutation(self):
        topics = [
            TopicScore(topic="a", score=0.9),
            TopicScore(topic="b", score=0.5),
            TopicScore(topic="c", score=0.3),
        ]
        result = CategorizationResult(primary_topic="a", topics=topics)
        before = [t.topic for t in result.topics]
        top = result.top_n(2)
        assert [t.topic for t in top] == ["a", "b"]
        assert [t.topic for t in result.topics] == before


# ---------------------------------------------------------------------------
# BUILTIN_TOPICS tests
# ---------------------------------------------------------------------------


class TestBuiltinTopics:
    """Tests for BUILTIN_TOPICS constant."""

    def test_builtin_topics_non_empty(self):
        """BUILTIN_TOPICS is a non-empty dict."""
        assert isinstance(BUILTIN_TOPICS, dict)
        assert len(BUILTIN_TOPICS) > 0

    def test_expected_topic_names(self):
        """Expected topic names are present."""
        expected = {
            "technology", "science", "health",
            "finance", "education", "business",
        }
        assert expected.issubset(set(BUILTIN_TOPICS.keys()))

    def test_all_topics_have_keywords(self):
        for name, keywords in BUILTIN_TOPICS.items():
            assert len(keywords) > 0, f"Topic '{name}' has no keywords"
            assert all(isinstance(kw, str) for kw in keywords)


# ---------------------------------------------------------------------------
# ContentCategorizer tests
# ---------------------------------------------------------------------------


class TestContentCategorizerInit:
    """Tests for ContentCategorizer initialization."""

    def test_init_has_builtin_topics(self):
        cat = ContentCategorizer()
        assert cat.get_topic("technology") is not None
        assert cat.get_topic("science") is not None

    def test_init_with_custom_topics(self):
        cat = ContentCategorizer(custom_topics={"gardening": ["plant", "soil"]})
        topic = cat.get_topic("gardening")
        assert topic is not None
        assert "plant" in topic.keywords

    def test_init_min_score(self):
        cat = ContentCategorizer(min_score=0.5)
        assert cat.min_score == 0.5

    def test_init_max_topics(self):
        cat = ContentCategorizer(max_topics=3)
        assert cat._max_topics == 3


class TestContentCategorizerTopics:
    """Tests for topic management methods."""

    def test_add_topic(self):
        cat = ContentCategorizer()
        topic = cat.add_topic("custom", ["kw1", "kw2"])
        assert topic.name == "custom"
        assert "kw1" in topic.keywords

    def test_add_topic_normalizes_name(self):
        cat = ContentCategorizer()
        cat.add_topic("CUSTOM", ["kw1"])
        assert cat.get_topic("custom") is not None

    def test_add_topic_returns_lowercased_name(self):
        cat = ContentCategorizer()
        topic = cat.add_topic("My Topic", ["kw1"])
        assert topic.name == "my topic"

    def test_add_topic_with_weight(self):
        cat = ContentCategorizer()
        topic = cat.add_topic("weighted", ["kw1"], weight=3.0)
        assert topic.weight == 3.0

    def test_remove_topic(self):
        cat = ContentCategorizer()
        cat.add_topic("temp", ["kw1"])
        assert cat.remove_topic("temp") is True
        assert cat.get_topic("temp") is None

    def test_remove_nonexistent_topic(self):
        cat = ContentCategorizer()
        assert cat.remove_topic("nonexistent") is False

    def test_get_topic(self):
        cat = ContentCategorizer()
        topic = cat.get_topic("technology")
        assert topic is not None
        assert topic.name == "technology"

    def test_get_nonexistent_topic(self):
        cat = ContentCategorizer()
        assert cat.get_topic("nonexistent") is None

    def test_get_topics_returns_list(self):
        cat = ContentCategorizer()
        topics = cat.get_topics()
        assert isinstance(topics, list)
        assert "technology" in topics


class TestContentCategorizerCategorize:
    """Tests for ContentCategorizer.categorize()."""

    @pytest.fixture
    def cat(self):
        return ContentCategorizer()

    def test_categorize_technology(self, cat):
        text = "Python programming software API developer framework"
        result = cat.categorize(text)
        assert result.primary_topic == "technology"

    def test_categorize_empty_text(self, cat):
        result = cat.categorize("")
        assert result.primary_topic == "unknown"
        assert result.topics == []

    def test_categorize_all_empty(self, cat):
        result = cat.categorize("", "", "", "")
        assert result.primary_topic == "unknown"
    def test_categorize_pins_returned_fields(self, cat):
        # Guard path: all-falsy input pins the exact returned object.
        guard = cat.categorize("", "", "", "")
        assert guard.primary_topic == "unknown"
        assert guard.topics == []
        assert guard.confidence == 0.0
        assert guard.reasons == ["no content provided"]
        assert guard.text_length == 0
        assert guard.keyword_count == 0

        # Normal path: a technology text pins the main-behavior fields.
        text = "Python programming software API developer framework"
        result = cat.categorize(text)
        assert result.primary_topic == "technology"
        assert result.confidence > 0.0
        assert result.text_length == len(text.split())
        assert result.keyword_count > 0
        assert len(result.topics) >= 1

    def test_categorize_no_match(self, cat):
        result = cat.categorize("xyz abc qwe random gibberish")
        # May still match some topics due to broad keywords
        assert isinstance(result, CategorizationResult)

    def test_categorize_title_boost(self, cat):
        text = "some random content"
        result = cat.categorize(text, title="Python API Framework")
        # Title keywords should boost technology score
        tech_score = next(
            (ts for ts in result.topics if ts.topic == "technology"), None
        )
        assert tech_score is not None

    def test_categorize_meta_description_boost(self, cat):
        text = "some random content"
        result = cat.categorize(
            text, meta_description="Python programming software development"
        )
        tech_score = next(
            (ts for ts in result.topics if ts.topic == "technology"), None
        )
        assert tech_score is not None

    def test_categorize_url_hint(self, cat):
        text = "some random content"
        result = cat.categorize(text, url="https://dev-blog.com/api")
        tech_score = next(
            (ts for ts in result.topics if ts.topic == "technology"), None
        )
        assert tech_score is not None

    def test_categorize_with_custom_topics(self):
        cat = ContentCategorizer(custom_topics={"cooking": ["recipe", "bake", "oven"]})
        result = cat.categorize("recipe for baking in the oven")
        cooking_score = next(
            (ts for ts in result.topics if ts.topic == "cooking"), None
        )
        assert cooking_score is not None

    def test_categorize_min_score_filter(self):
        cat = ContentCategorizer(min_score=0.5)
        result = cat.categorize("slightly related")
        for ts in result.topics:
            assert ts.score >= 0.5

    def test_categorize_max_topics_limit(self):
        cat = ContentCategorizer(max_topics=2)
        text = (
            "Python programming software API developer machine learning "
            "algorithm database server cloud docker kubernetes"
        )
        result = cat.categorize(text)
        assert len(result.topics) <= 2

    def test_categorize_science(self, cat):
        text = "quantum physics experiment hypothesis peer review"
        result = cat.categorize(text)
        science_score = next(
            (ts for ts in result.topics if ts.topic == "science"), None
        )
        assert science_score is not None

    def test_categorize_health(self, cat):
        text = "medical doctor hospital treatment therapy diagnosis"
        result = cat.categorize(text)
        health_score = next(
            (ts for ts in result.topics if ts.topic == "health"), None
        )
        assert health_score is not None

    def test_categorize_finance(self, cat):
        text = "stock market investment portfolio trading equity"
        result = cat.categorize(text)
        finance_score = next(
            (ts for ts in result.topics if ts.topic == "finance"), None
        )
        assert finance_score is not None

    def test_categorize_education(self, cat):
        text = "learning course curriculum syllabus lecture tutorial"
        result = cat.categorize(text)
        edu_score = next(
            (ts for ts in result.topics if ts.topic == "education"), None
        )
        assert edu_score is not None

    def test_categorize_business(self, cat):
        text = "startup entrepreneur venture capital funding pitch"
        result = cat.categorize(text)
        biz_score = next(
            (ts for ts in result.topics if ts.topic == "business"), None
        )
        assert biz_score is not None


class TestContentCategorizerBatch:
    """Tests for batch categorization."""

    def test_categorize_batch(self):
        cat = ContentCategorizer()
        items = [
            {"text": "Python programming API", "title": "Tech"},
            {"text": "stock market investment", "title": "Finance"},
        ]
        results = cat.categorize_batch(items)
        assert len(results) == 2
        assert results[0].primary_topic == "technology"
        assert results[1].primary_topic == "finance"

    def test_categorize_batch_empty(self):
        cat = ContentCategorizer()
        results = cat.categorize_batch([])
        assert results == []


class TestContentCategorizerInternal:
    """Tests for internal methods."""

    def test_extract_url_hints_tech(self):
        cat = ContentCategorizer()
        hints = cat._extract_url_hints("https://dev-blog.com/api")
        assert "technology" in hints

    def test_extract_url_hints_health(self):
        cat = ContentCategorizer()
        hints = cat._extract_url_hints("https://healthcare.com/clinic")
        assert "health" in hints

    def test_extract_url_hints_empty(self):
        cat = ContentCategorizer()
        hints = cat._extract_url_hints("")
        assert hints == set()


    def test_extract_url_hints_no_tld_false_positive(self):
        """A plain *.com URL must not yield a spurious business hint.

        The TLD "com" must not match hint words that merely contain it
        (e.g. "corp" -> business, "eco" -> environment).
        """
        cat = ContentCategorizer()
        hints = cat._extract_url_hints("https://example.com/")
        assert "business" not in hints
        assert "environment" not in hints
        # intended match still works
        hints2 = cat._extract_url_hints("https://dev-blog.com/api")
        assert "technology" in hints2
        assert "business" not in hints2
    def test_score_topic_returns_tuple(self):
        cat = ContentCategorizer()
        topic = TopicCategory(name="tech", keywords=["python", "code"])
        result = cat._score_topic(
            topic=topic,
            text_tokens={"python", "code", "hello"},
            title_tokens=set(),
            meta_tokens=set(),
            text_lower="python code hello",
            title_lower="",
            meta_lower="",
            url_hints=set(),
        )
        assert len(result) == 3
        score, matched, sources = result
        assert isinstance(score, float)
        assert isinstance(matched, list)
        assert isinstance(sources, list)

    def test_score_topic_title_only_source_label(self):
        """A keyword matched only in the title must be labeled 'title', not 'text'."""
        cat = ContentCategorizer()
        topic = TopicCategory(name="tech", keywords=["python"])
        _score, matched, sources = cat._score_topic(
            topic=topic,
            text_tokens=set(),
            title_tokens={"python"},
            meta_tokens=set(),
            text_lower="",
            title_lower="python",
            meta_lower="",
            url_hints=set(),
        )
        assert matched == ["python"]
        assert sources == ["title"]
        assert "text" not in sources

    def test_score_topic_meta_only_source_label(self):
        """A keyword matched only in the meta description must be labeled 'meta_description'."""
        cat = ContentCategorizer()
        topic = TopicCategory(name="tech", keywords=["python"])
        _score, matched, sources = cat._score_topic(
            topic=topic,
            text_tokens=set(),
            title_tokens=set(),
            meta_tokens={"python"},
            text_lower="",
            title_lower="",
            meta_lower="python",
            url_hints=set(),
        )
        assert matched == ["python"]
        assert sources == ["meta_description"]
        assert "text" not in sources

    def test_score_topic_text_and_title_sources(self):
        """Text and title matches produce distinct, correctly-labeled sources."""
        cat = ContentCategorizer()
        topic = TopicCategory(name="tech", keywords=["python", "code"])
        _score, matched, sources = cat._score_topic(
            topic=topic,
            text_tokens={"python"},
            title_tokens={"code"},
            meta_tokens=set(),
            text_lower="python",
            title_lower="code",
            meta_lower="",
            url_hints=set(),
        )
        assert sorted(matched) == ["code", "python"]
        assert sources == ["text", "title"]

    def test_match_keywords_single_word(self):
        cat = ContentCategorizer()
        matches = cat._match_keywords(
            keywords=["python", "java", "rust"],
            tokens={"python", "hello", "world"},
            raw_text="python hello world",
        )
        assert "python" in matches

    def test_match_keywords_multi_word(self):
        cat = ContentCategorizer()
        matches = cat._match_keywords(
            keywords=["machine learning", "deep learning"],
            tokens={"machine", "learning", "deep"},
            raw_text="machine learning and deep learning",
        )
        assert "machine learning" in matches
        assert "deep learning" in matches

    def test_build_reasons_no_match(self):
        cat = ContentCategorizer()
        reasons = cat._build_reasons([], "text")
        assert "no matching topics" in reasons[0]

    def test_build_reasons_with_scores(self):
        cat = ContentCategorizer()
        scores = [
            TopicScore(topic="tech", score=0.9, matched_keywords=["api", "code"], signal_sources=["text"]),
        ]
        reasons = cat._build_reasons(scores, "text")
        assert len(reasons) > 0
        assert "tech" in reasons[0]
        assert "keywords=" in reasons[0]
