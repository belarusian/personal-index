"""Tests for content recommendation engine."""

from __future__ import annotations

from personal_index.content_recommender import (
    ContentItem,
    Recommendation,
    Recommender,
    _extract_keywords,
)


class TestExtractKeywords:
    def test_basic_extraction(self):
        keywords = _extract_keywords("Python programming language tutorial")
        assert "python" in keywords
        assert "programming" in keywords
        assert "language" in keywords
        assert "tutorial" in keywords

    def test_stopwords_removed(self):
        keywords = _extract_keywords("the and or but in on at")
        assert len(keywords) == 0

    def test_empty_text(self):
        assert _extract_keywords("") == set()

    def test_short_words_removed(self):
        keywords = _extract_keywords("an is it")
        assert len(keywords) == 0


class TestContentItem:
    def test_all_keywords(self):
        item = ContentItem(
            url="https://example.com",
            title="Python Tutorial",
            content="Learn Python programming",
            keywords=["python"],
        )
        kws = item.all_keywords
        assert "python" in kws
        assert "tutorial" in kws
        assert "learn" in kws
        assert "programming" in kws


class TestRecommendation:
    def test_to_dict(self):
        rec = Recommendation(
            url="https://example.com",
            title="Test Page",
            score=0.85,
            reason="keywords: python",
            matching_keywords=["python"],
            matching_tags=["tech"],
        )
        d = rec.to_dict()
        assert d["url"] == "https://example.com"
        assert d["title"] == "Test Page"
        assert d["score"] == 0.85
        assert d["reason"] == "keywords: python"
        assert d["matching_keywords"] == ["python"]
        assert d["matching_tags"] == ["tech"]


class TestRecommender:
    def setup_method(self):
        self.recommender = Recommender(min_score=0.0)
        self.recommender.add_items([
            ContentItem(
                url="https://example.com/python",
                title="Python Tutorial",
                content="Learn Python programming basics",
                keywords=["python", "tutorial"],
                tags=["programming", "python"],
                score=8.0,
            ),
            ContentItem(
                url="https://example.com/javascript",
                title="JavaScript Guide",
                content="Learn JavaScript web development",
                keywords=["javascript", "web"],
                tags=["programming", "web"],
                score=7.0,
            ),
            ContentItem(
                url="https://example.com/data-science",
                title="Data Science with Python",
                content="Python for data science and machine learning",
                keywords=["python", "data-science", "ml"],
                tags=["programming", "data"],
                score=9.0,
            ),
        ])

    def test_recommend_by_keyword_overlap(self):
        seed = ContentItem(
            url="https://example.com/seed",
            title="Python Basics",
            content="Introduction to Python",
            keywords=["python"],
        )
        recs = self.recommender.recommend(seed, top_n=3)
        assert len(recs) >= 1
        # Python pages should rank higher
        assert recs[0].url in [
            "https://example.com/python",
            "https://example.com/data-science",
        ]

    def test_recommend_by_tag_similarity(self):
        seed = ContentItem(
            url="https://example.com/seed",
            title="Web Dev",
            content="",
            tags=["programming", "web"],
        )
        recs = self.recommender.recommend(seed, top_n=3, tag_weight=0.8)
        assert len(recs) >= 1
        # JavaScript page should rank high due to tag match
        assert any("javascript" in r.url for r in recs)

    def test_recommend_empty_pool(self):
        empty = Recommender()
        seed = ContentItem(url="https://x.com", title="X")
        assert empty.recommend(seed) == []

    def test_recommend_excludes_seed(self):
        seed = ContentItem(
            url="https://example.com/python",
            title="Python Tutorial",
            content="Learn Python",
        )
        recs = self.recommender.recommend(seed, top_n=10)
        urls = [r.url for r in recs]
        assert "https://example.com/python" not in urls

    def test_recommend_for_keywords(self):
        recs = self.recommender.recommend_for_keywords(["python"], top_n=3)
        assert len(recs) >= 2
        for r in recs:
            assert "python" in r.matching_keywords

    def test_recommend_for_keywords_empty(self):
        recs = self.recommender.recommend_for_keywords([], top_n=3)
        assert recs == []

    def test_clear(self):
        self.recommender.clear()
        assert self.recommender.item_count == 0

    def test_item_count(self):
        assert self.recommender.item_count == 3

    def test_min_score_filtering(self):
        recommender = Recommender(min_score=0.9)
        recommender.add_items([
            ContentItem(
                url="https://example.com/python",
                title="Python Tutorial",
                content="Learn Python programming basics",
                keywords=["python"],
            ),
        ])
        seed = ContentItem(
            url="https://example.com/seed",
            title="Unrelated",
            content="Something completely different",
        )
        recs = recommender.recommend(seed, top_n=5)
        assert len(recs) == 0

    def test_custom_weights(self):
        seed = ContentItem(
            url="https://example.com/seed",
            title="Python Basics",
            content="Introduction to Python",
            keywords=["python"],
        )
        # High keyword weight should favor keyword matches
        recs_kw = self.recommender.recommend(seed, keyword_weight=0.9, tag_weight=0.05, score_weight=0.05)
        assert len(recs_kw) >= 1
        assert "python" in recs_kw[0].url
