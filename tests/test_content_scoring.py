"""Tests for content scoring module."""

import pytest
from personal_index.content_scoring import ContentScorer, ScoreBreakdown


class TestScoreBreakdown:
    def test_default_values(self):
        b = ScoreBreakdown()
        assert b.total_score == 0.0
        assert b.content_length_score == 0.0


class TestContentScorer:
    def _make_content(self, text="", keywords=None, headings=None,
                      links=None, images=None):
        return {
            "text": text,
            "keywords": keywords or [],
            "headings": headings or [],
            "links": links or [],
            "images": images or [],
        }

    def test_score_returns_breakdown(self):
        scorer = ContentScorer()
        score, breakdown = scorer.score(self._make_content(text="hello world"))
        assert isinstance(score, float)
        assert isinstance(breakdown, ScoreBreakdown)

    def test_content_length_short(self):
        scorer = ContentScorer()
        _, breakdown = scorer.score(self._make_content(text="short"))
        assert breakdown.content_length_score < 0.5

    def test_content_length_optimal(self):
        text = "word " * 500  # 500 words
        scorer = ContentScorer()
        _, breakdown = scorer.score(self._make_content(text=text))
        assert breakdown.content_length_score == 1.0

    def test_content_length_very_long(self):
        text = "word " * 5000  # 5000 words
        scorer = ContentScorer()
        _, breakdown = scorer.score(self._make_content(text=text))
        assert breakdown.content_length_score < 1.0

    def test_keyword_density_match(self):
        scorer = ContentScorer()
        content = self._make_content(
            text="Python programming language is great",
            keywords=["python", "programming"],
        )
        _, breakdown = scorer.score(content)
        assert breakdown.keyword_density_score > 0.5

    def test_keyword_density_no_match(self):
        scorer = ContentScorer()
        content = self._make_content(
            text="Hello world",
            keywords=["python", "programming"],
        )
        _, breakdown = scorer.score(content)
        assert breakdown.keyword_density_score == 0.0

    def test_keyword_density_no_keywords(self):
        scorer = ContentScorer()
        content = self._make_content(text="Hello world", keywords=[])
        _, breakdown = scorer.score(content)
        assert breakdown.keyword_density_score == 0.5

    def test_heading_score_with_h1(self):
        scorer = ContentScorer()
        content = self._make_content(headings=["h1: Title", "h2: Sub"])
        _, breakdown = scorer.score(content)
        assert breakdown.heading_score > 0.0

    def test_heading_score_no_headings(self):
        scorer = ContentScorer()
        content = self._make_content(headings=[])
        _, breakdown = scorer.score(content)
        assert breakdown.heading_score == 0.0

    def test_link_score_moderate(self):
        scorer = ContentScorer()
        links = [{"url": f"http://example.com/{i}"} for i in range(10)]
        content = self._make_content(links=links)
        _, breakdown = scorer.score(content)
        assert 0.3 < breakdown.link_score <= 1.0

    def test_link_score_too_many(self):
        scorer = ContentScorer()
        links = [{"url": f"http://example.com/{i}"} for i in range(150)]
        content = self._make_content(links=links)
        _, breakdown = scorer.score(content)
        assert breakdown.link_score == 0.2

    def test_link_score_none(self):
        scorer = ContentScorer()
        content = self._make_content(links=[])
        _, breakdown = scorer.score(content)
        assert breakdown.link_score == 0.3

    def test_image_score_with_alt(self):
        scorer = ContentScorer()
        images = [{"src": "img.png", "alt": "Description"}]
        content = self._make_content(images=images)
        _, breakdown = scorer.score(content)
        assert breakdown.image_score == 1.0

    def test_image_score_no_alt(self):
        scorer = ContentScorer()
        images = [{"src": "img.png", "alt": ""}]
        content = self._make_content(images=images)
        _, breakdown = scorer.score(content)
        assert breakdown.image_score == 0.0

    def test_readability_optimal(self):
        # Words of 4-7 chars
        text = "The quick brown fox jumps over the lazy dog"
        scorer = ContentScorer()
        _, breakdown = scorer.score(self._make_content(text=text))
        assert breakdown.readability_score >= 0.7

    def test_rank_items(self):
        scorer = ContentScorer()
        items = [
            self._make_content(text="word " * 500, keywords=["word"]),
            self._make_content(text="short"),
        ]
        ranked = scorer.rank(items)
        assert len(ranked) == 2
        assert ranked[0][1] >= ranked[1][1]

    def test_custom_weights(self):
        weights = {"content_length": 1.0, "keyword_density": 0, "headings": 0,
                   "links": 0, "images": 0, "readability": 0, "freshness": 0}
        scorer = ContentScorer(weights=weights)
        _score, breakdown = scorer.score(self._make_content(text="word " * 500))
        assert breakdown.total_score == breakdown.content_length_score
