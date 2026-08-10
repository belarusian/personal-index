"""Tests for content categorizer module."""

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
# Data structure tests
# ---------------------------------------------------------------------------


class TestTopicCategory:
    """Tests for TopicCategory dataclass."""

    def test_topic_creation(self):
        topic = TopicCategory(
            name="test",
            keywords=["keyword1", "Keyword2"],
            description="A test topic",
            weight=1.5,
        )
        assert topic.name == "test"
        assert "keyword1" in topic.keywords
        assert "keyword2" in topic.keywords  # normalized to lowercase
        assert topic.description == "A test topic"
        assert topic.weight == 1.5

    def test_topic_default_values(self):
        topic = TopicCategory(name="minimal")
        assert topic.keywords == []
        assert topic.description == ""
        assert topic.weight == 1.0

    def test_topic_keyword_normalization(self):
        topic = TopicCategory(name="test", keywords=["UPPER", "MiXeD"])
        assert "upper" in topic.keywords
        assert "mixed" in topic.keywords


class TestTopicScore:
    """Tests for TopicScore dataclass."""

    def test_topic_score_creation(self):
        ts = TopicScore(topic="tech", score=0.85, matched_keywords=["api", "code"])
        assert ts.topic == "tech"
        assert ts.score == 0.85
        assert ts.matched_keywords == ["api", "code"]

    def test_topic_score_comparison(self):
        ts1 = TopicScore(topic="a", score=0.5)
        ts2 = TopicScore(topic="b", score=0.8)
        assert ts2 > ts1
        assert ts1 < ts2

    def test_topic_score_default_values(self):
        ts = TopicScore(topic="test", score=0.0)
        assert ts.matched_keywords == []
        assert ts.signal_sources == []


class TestCategorizationResult:
    """Tests for CategorizationResult dataclass."""

    def test_result_creation(self):
        result = CategorizationResult(
            primary_topic="technology",
            topics=[
                TopicScore(topic="technology", score=0.9),
                TopicScore(topic="science", score=0.5),
            ],
            confidence=0.9,
        )
        assert result.primary_topic == "technology"
        assert result.confidence == 0.9
        assert len(result.topics) == 2

    def test_secondary_topics(self):
        result = CategorizationResult(
            primary_topic="tech",
            topics=[
                TopicScore(topic="tech", score=0.9),
                TopicScore(topic="science", score=0.5),
                TopicScore(topic="business", score=0.3),
            ],
        )
        secondary = result.secondary_topics
        assert len(secondary) == 2
        assert secondary[0].topic == "science"
        assert secondary[1].topic == "business"

    def test_secondary_topics_empty(self):
        result = CategorizationResult(
            primary_topic="tech",
            topics=[TopicScore(topic="tech", score=0.9)],
        )
        assert result.secondary_topics == []

    def test_top_n(self):
        result = CategorizationResult(
            primary_topic="tech",
            topics=[
                TopicScore(topic="tech", score=0.9),
                TopicScore(topic="science", score=0.5),
                TopicScore(topic="business", score=0.3),
                TopicScore(topic="health", score=0.1),
            ],
        )
        top2 = result.top_n(2)
        assert len(top2) == 2
        assert top2[0].topic == "tech"
        assert top2[1].topic == "science"

    def test_top_n_exceeds_available(self):
        result = CategorizationResult(
            primary_topic="tech",
            topics=[TopicScore(topic="tech", score=0.9)],
        )
        top5 = result.top_n(5)
        assert len(top5) == 1


# ---------------------------------------------------------------------------
# Built-in topics tests
# ---------------------------------------------------------------------------


class TestBuiltinTopics:
    """Tests for built-in topic definitions."""

    def test_builtin_topics_exist(self):
        expected = {
            "technology", "science", "health", "finance", "education",
            "business", "entertainment", "sports", "travel", "food",
            "politics", "environment",
        }
        assert set(BUILTIN_TOPICS.keys()) == expected

    def test_builtin_topics_have_keywords(self):
        for name, keywords in BUILTIN_TOPICS.items():
            assert len(keywords) > 0, f"Topic '{name}' has no keywords"
            assert all(isinstance(kw, str) for kw in keywords), \
                f"Topic '{name}' has non-string keywords"

    def test_builtin_topics_no_empty_keywords(self):
        for name, keywords in BUILTIN_TOPICS.items():
            assert all(kw.strip() for kw in keywords), \
                f"Topic '{name}' has empty keyword strings"


# ---------------------------------------------------------------------------
# ContentCategorizer tests
# ---------------------------------------------------------------------------


class TestContentCategorizer:
    """Tests for ContentCategorizer class."""

    def setup_method(self):
        self.categorizer = ContentCategorizer()

    # --- Initialization ---

    def test_init_has_builtin_topics(self):
        topics = self.categorizer.get_topics()
        assert "technology" in topics
        assert "science" in topics
        assert "health" in topics

    def test_init_with_custom_topics(self):
        custom = {"cooking": ["recipe", "baking", "ingredient"]}
        cat = ContentCategorizer(custom_topics=custom)
        assert "cooking" in cat.get_topics()

    def test_init_min_score(self):
        cat = ContentCategorizer(min_score=0.5)
        assert cat.min_score == 0.5

    def test_init_max_topics(self):
        cat = ContentCategorizer(max_topics=3)
        assert cat._max_topics == 3

    # --- Topic management ---

    def test_add_topic(self):
        topic = self.categorizer.add_topic("mytopic", ["kw1", "kw2"])
        assert topic.name == "mytopic"
        assert "mytopic" in self.categorizer.get_topics()

    def test_add_topic_normalizes_name(self):
        self.categorizer.add_topic("MyTopic", ["kw1"])
        assert "mytopic" in self.categorizer.get_topics()

    def test_add_topic_with_weight(self):
        topic = self.categorizer.add_topic("weighted", ["kw1"], weight=2.0)
        assert topic.weight == 2.0

    def test_remove_topic(self):
        self.categorizer.add_topic("temp", ["kw1"])
        assert self.categorizer.remove_topic("temp") is True
        assert "temp" not in self.categorizer.get_topics()

    def test_remove_nonexistent_topic(self):
        assert self.categorizer.remove_topic("nonexistent") is False

    def test_get_topic(self):
        self.categorizer.add_topic("custom", ["kw1", "kw2"])
        topic = self.categorizer.get_topic("custom")
        assert topic is not None
        assert topic.name == "custom"

    def test_get_nonexistent_topic(self):
        assert self.categorizer.get_topic("nonexistent") is None

    # --- Categorization: technology ---

    def test_categorize_technology_text(self):
        text = (
            "Python is a popular programming language used for software "
            "development. The API framework provides a robust library for "
            "building scalable microservices with docker and kubernetes."
        )
        result = self.categorizer.categorize(text)
        assert result.primary_topic == "technology"
        assert result.confidence > 0

    def test_categorize_technology_title_boost(self):
        text = "Some general content about various things."
        title = "Python Programming and API Development"
        result = self.categorizer.categorize(text=text, title=title)
        # Title should boost technology even with generic text
        tech_score = next(
            (ts for ts in result.topics if ts.topic == "technology"), None
        )
        assert tech_score is not None

    # --- Categorization: science ---

    def test_categorize_science_text(self):
        text = (
            "The quantum physics experiment revealed new insights about "
            "molecular behavior. Researchers published their findings in a "
            "peer-reviewed journal after extensive laboratory observation."
        )
        result = self.categorizer.categorize(text)
        assert result.primary_topic == "science"

    # --- Categorization: health ---

    def test_categorize_health_text(self):
        text = (
            "The doctor recommended a new treatment plan for the patient's "
            "chronic condition. Clinical trials showed promising results for "
            "the medication, with improved mental health outcomes."
        )
        result = self.categorizer.categorize(text)
        assert result.primary_topic == "health"

    # --- Categorization: finance ---

    def test_categorize_finance_text(self):
        text = (
            "The stock market saw significant growth in the equity sector. "
            "Investment portfolios diversified with bonds and ETFs. The "
            "interest rate decision by the central bank affected trading."
        )
        result = self.categorizer.categorize(text)
        assert result.primary_topic == "finance"

    # --- Categorization: education ---

    def test_categorize_education_text(self):
        text = (
            "The online course curriculum covers advanced topics in the "
            "university syllabus. Students prepare for the final exam with "
            "tutorial assignments and lecture notes."
        )
        result = self.categorizer.categorize(text)
        assert result.primary_topic == "education"

    # --- Categorization: business ---

    def test_categorize_business_text(self):
        text = (
            "The startup launched its MVP product with a strong marketing "
            "strategy. The CEO focused on team culture and scaling the "
            "business through venture capital funding."
        )
        result = self.categorizer.categorize(text)
        assert result.primary_topic == "business"

    # --- Categorization: entertainment ---

    def test_categorize_entertainment_text(self):
        text = (
            "The new movie starring the famous actor won the Oscar award. "
            "The music album topped the charts and the concert festival "
            "drew thousands of fans."
        )
        result = self.categorizer.categorize(text)
        assert result.primary_topic == "entertainment"

    # --- Categorization: sports ---

    def test_categorize_sports_text(self):
        text = (
            "The football team won the championship with a last-minute goal. "
            "The player's training and endurance were key to the victory "
            "in the league tournament."
        )
        result = self.categorizer.categorize(text)
        assert result.primary_topic == "sports"

    # --- Categorization: travel ---

    def test_categorize_travel_text(self):
        text = (
            "Our vacation trip to the destination included a hotel booking "
            "and flight reservation. The local culture and landmarks made "
            "it an unforgettable adventure journey."
        )
        result = self.categorizer.categorize(text)
        assert result.primary_topic == "travel"

    # --- Categorization: food ---

    def test_categorize_food_text(self):
        text = (
            "The chef prepared a gourmet recipe using organic ingredients. "
            "The restaurant's fine dining menu featured seasonal cuisine "
            "with wine pairings."
        )
        result = self.categorizer.categorize(text)
        assert result.primary_topic == "food"

    # --- Categorization: politics ---

    def test_categorize_politics_text(self):
        text = (
            "The election campaign focused on policy changes. The president "
            "signed new legislation in congress while the senate debated "
            "the constitutional amendment."
        )
        result = self.categorizer.categorize(text)
        assert result.primary_topic == "politics"

    # --- Categorization: environment ---

    def test_categorize_environment_text(self):
        text = (
            "Climate change and global warming require renewable energy "
            "solutions. Solar and wind power reduce carbon footprint and "
            "promote sustainability and eco-friendly practices."
        )
        result = self.categorizer.categorize(text)
        assert result.primary_topic == "environment"

    # --- Multi-signal categorization ---

    def test_categorize_with_url_hint(self):
        text = "Some content about programming and software."
        url = "https://tech-blog.example.com/article"
        result = self.categorizer.categorize(text=text, url=url)
        tech_score = next(
            (ts for ts in result.topics if ts.topic == "technology"), None
        )
        assert tech_score is not None
        assert "url_hint" in tech_score.signal_sources

    def test_categorize_with_meta_description(self):
        text = "Brief content here."
        meta = "A comprehensive guide to machine learning and artificial intelligence"
        result = self.categorizer.categorize(text=text, meta_description=meta)
        tech_score = next(
            (ts for ts in result.topics if ts.topic == "technology"), None
        )
        assert tech_score is not None
        assert "meta_description" in tech_score.signal_sources

    def test_categorize_title_boosts_score(self):
        text = "Some general content about various things."
        title = "Machine Learning and Artificial Intelligence"
        result = self.categorizer.categorize(text=text, title=title)
        tech_score = next(
            (ts for ts in result.topics if ts.topic == "technology"), None
        )
        assert tech_score is not None
        assert "title" in tech_score.signal_sources

    # --- Edge cases ---

    def test_categorize_empty_text(self):
        result = self.categorizer.categorize("")
        assert result.primary_topic == "unknown"
        assert result.confidence == 0.0
        assert result.topics == []

    def test_categorize_all_empty(self):
        result = self.categorizer.categorize(
            text="", title="", url="", meta_description=""
        )
        assert result.primary_topic == "unknown"
        assert result.confidence == 0.0

    def test_categorize_no_match(self):
        text = "xkcd qwerty zzzz abcdefg random gibberish"
        result = self.categorizer.categorize(text)
        # Should be uncategorized or have very low confidence
        assert result.confidence < 0.3

    def test_categorize_short_text(self):
        text = "hello world"
        result = self.categorizer.categorize(text)
        assert isinstance(result, CategorizationResult)

    def test_categorization_result_has_reasons(self):
        text = "Python programming and software development"
        result = self.categorizer.categorize(text)
        assert len(result.reasons) > 0
        assert all(isinstance(r, str) for r in result.reasons)

    def test_categorization_result_text_length(self):
        text = "one two three four five"
        result = self.categorizer.categorize(text)
        assert result.text_length == 5

    def test_categorization_result_keyword_count(self):
        text = "python python java java"
        result = self.categorizer.categorize(text)
        assert result.keyword_count >= 2

    # --- Batch categorization ---

    def test_categorize_batch(self):
        items = [
            {
                "text": "Python programming and API development",
                "title": "Tech Article",
            },
            {
                "text": "The stock market investment portfolio",
                "title": "Finance News",
            },
        ]
        results = self.categorizer.categorize_batch(items)
        assert len(results) == 2
        assert results[0].primary_topic == "technology"
        assert results[1].primary_topic == "finance"

    def test_categorize_batch_empty(self):
        results = self.categorizer.categorize_batch([])
        assert results == []

    def test_categorize_batch_with_all_fields(self):
        items = [
            {
                "text": "machine learning algorithm",
                "title": "AI Research",
                "url": "https://tech.example.com/ml",
                "meta_description": "deep learning neural network",
            },
        ]
        results = self.categorizer.categorize_batch(items)
        assert len(results) == 1
        assert results[0].primary_topic == "technology"

    # --- Custom topics ---

    def test_custom_topic_categorization(self):
        cat = ContentCategorizer(
            custom_topics={"gardening": ["plant", "soil", "garden", "seed"]}
        )
        text = "The garden soil needs more nutrients for the plant seeds."
        result = cat.categorize(text)
        gardening_score = next(
            (ts for ts in result.topics if ts.topic == "gardening"), None
        )
        assert gardening_score is not None

    def test_custom_topic_overrides_builtin(self):
        cat = ContentCategorizer()
        cat.add_topic("technology", ["custom_kw"], weight=10.0)
        text = "custom_kw appears here"
        result = cat.categorize(text)
        assert result.primary_topic == "technology"

    def test_custom_topic_weight(self):
        cat = ContentCategorizer()
        cat.add_topic("important", ["key1", "key2"], weight=5.0)
        text = "key1 and key2 are mentioned"
        result = cat.categorize(text)
        imp_score = next(
            (ts for ts in result.topics if ts.topic == "important"), None
        )
        assert imp_score is not None

    # --- Max topics ---

    def test_max_topics_limit(self):
        cat = ContentCategorizer(max_topics=2)
        text = (
            "Python programming software API developer machine learning "
            "algorithm database server cloud docker kubernetes"
        )
        result = cat.categorize(text)
        assert len(result.topics) <= 2

    # --- Min score ---

    def test_min_score_filter(self):
        cat = ContentCategorizer(min_score=0.5)
        text = "slightly related content"
        result = cat.categorize(text)
        for ts in result.topics:
            assert ts.score >= 0.5

    # --- URL hint extraction ---

    def test_url_hint_tech(self):
        hints = self.categorizer._extract_url_hints("https://dev-blog.com/api")
        assert "technology" in hints

    def test_url_hint_health(self):
        hints = self.categorizer._extract_url_hints("https://healthcare.com/clinic")
        assert "health" in hints

    def test_url_hint_empty_url(self):
        hints = self.categorizer._extract_url_hints("")
        assert hints == set()

    def test_url_hint_no_match(self):
        hints = self.categorizer._extract_url_hints("https://random-domain.com/page")
        # May or may not match depending on domain parts
        assert isinstance(hints, set)

    # --- Score topic ---

    def test_score_topic_returns_tuple(self):
        topic = TopicCategory(name="tech", keywords=["python", "code"])
        text_tokens = {"python", "code", "hello"}
        result = self.categorizer._score_topic(
            topic=topic,
            text_tokens=text_tokens,
            title_tokens=set(),
            meta_tokens=set(),
            text_lower="",
            title_lower="",
            meta_lower="",
            url_hints=set(),
        )
        assert len(result) == 3
        score, matched, sources = result
        assert isinstance(score, float)
        assert isinstance(matched, list)
        assert isinstance(sources, list)

    # --- Reasons ---

    def test_reasons_for_no_match(self):
        result = self.categorizer.categorize("xyz abc qwe")
        if result.topics:
            assert len(result.reasons) > 0
        else:
            assert "no matching topics" in result.reasons[0]

    def test_reasons_include_keyword_preview(self):
        text = "python programming software development api framework"
        result = self.categorizer.categorize(text)
        if result.reasons:
            assert "keywords=" in result.reasons[0]
