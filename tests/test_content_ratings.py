"""Tests for content_ratings - rate saved items 1-5 stars."""

from __future__ import annotations

import pytest

from personal_index.content_ratings import (
    Rating,
    RatingStore,
    RatingStats,
)


class TestRatingModel:
    """Tests for Rating dataclass."""

    def test_rating_creation_min(self):
        rating = Rating(content_id="c1", score=1)
        assert rating.score == 1

    def test_rating_creation_max(self):
        rating = Rating(content_id="c1", score=5)
        assert rating.score == 5

    def test_rating_creation_mid(self):
        rating = Rating(content_id="c1", score=3)
        assert rating.score == 3

    def test_rating_score_too_low(self):
        with pytest.raises(ValueError):
            Rating(content_id="c1", score=0)

    def test_rating_score_too_high(self):
        with pytest.raises(ValueError):
            Rating(content_id="c1", score=6)

    def test_rating_score_float(self):
        rating = Rating(content_id="c1", score=3.5)
        assert rating.score == 3.5

    def test_rating_score_float_negative(self):
        with pytest.raises(ValueError):
            Rating(content_id="c1", score=-1.0)

    def test_rating_score_float_over_max(self):
        with pytest.raises(ValueError):
            Rating(content_id="c1", score=5.5)

    def test_rating_with_comment(self):
        rating = Rating(content_id="c1", score=4, comment="Great article")
        assert rating.comment == "Great article"

    def test_rating_with_author(self):
        rating = Rating(content_id="c1", score=4, author="alice")
        assert rating.author == "alice"

    def test_rating_to_dict(self):
        rating = Rating(content_id="c1", score=4, comment="Good")
        d = rating.to_dict()
        assert d["content_id"] == "c1"
        assert d["score"] == 4
        assert d["comment"] == "Good"

    def test_rating_from_dict(self):
        data = {
            "content_id": "c1",
            "score": 4,
            "comment": "Good",
            "author": "alice",
            "rating_id": "abc123",
            "created_at": "2024-01-01T00:00:00",
        }
        rating = Rating.from_dict(data)
        assert rating.content_id == "c1"
        assert rating.score == 4
        assert rating.comment == "Good"
        assert rating.author == "alice"

    def test_rating_repr(self):
        rating = Rating(content_id="c1", score=5)
        assert "c1" in repr(rating)
        assert "5" in repr(rating)

    def test_rating_star_string(self):
        rating = Rating(content_id="c1", score=3)
        assert rating.star_string() == "★★★☆☆"

    def test_rating_star_string_half(self):
        rating = Rating(content_id="c1", score=3.5)
        assert rating.star_string() == "★★★½☆"

    def test_rating_star_string_full(self):
        rating = Rating(content_id="c1", score=5)
        assert rating.star_string() == "★★★★★"

    def test_rating_star_string_empty(self):
        rating = Rating(content_id="c1", score=1)
        assert rating.star_string() == "★☆☆☆☆"


class TestRatingStore:
    """Tests for RatingStore class."""

    def setup_method(self):
        self.store = RatingStore()

    def test_rate_content(self):
        result = self.store.rate("c1", 4)
        assert result is not None
        assert result.score == 4

    def test_rate_content_with_comment(self):
        result = self.store.rate("c1", 4, comment="Great")
        assert result.comment == "Great"

    def test_rate_content_with_author(self):
        result = self.store.rate("c1", 4, author="alice")
        assert result.author == "alice"

    def test_rate_invalid_score_low(self):
        with pytest.raises(ValueError):
            self.store.rate("c1", 0)

    def test_rate_invalid_score_high(self):
        with pytest.raises(ValueError):
            self.store.rate("c1", 6)

    def test_get_rating(self):
        self.store.rate("c1", 4)
        rating = self.store.get_rating("c1")
        assert rating is not None
        assert rating.score == 4

    def test_get_rating_nonexistent(self):
        assert self.store.get_rating("c1") is None

    def test_update_rating(self):
        self.store.rate("c1", 3)
        self.store.rate("c1", 5)
        rating = self.store.get_rating("c1")
        assert rating.score == 5

    def test_update_rating_preserves_author(self):
        self.store.rate("c1", 3, author="alice")
        self.store.rate("c1", 5)
        rating = self.store.get_rating("c1")
        assert rating.score == 5
        assert rating.author == "alice"

    def test_remove_rating(self):
        self.store.rate("c1", 4)
        result = self.store.remove_rating("c1")
        assert result is True
        assert self.store.get_rating("c1") is None

    def test_remove_nonexistent_rating(self):
        result = self.store.remove_rating("c1")
        assert result is False

    def test_list_rated_content(self):
        self.store.rate("c1", 3)
        self.store.rate("c2", 4)
        self.store.rate("c3", 5)
        rated = self.store.list_rated_content()
        assert len(rated) == 3

    def test_list_rated_content_empty(self):
        assert self.store.list_rated_content() == []

    def test_list_rated_content_sorted_by_score(self):
        self.store.rate("c1", 3)
        self.store.rate("c2", 5)
        self.store.rate("c3", 4)
        rated = self.store.list_rated_content(sort_by="score")
        scores = [r.score for r in rated]
        assert scores == [5, 4, 3]

    def test_list_rated_content_sorted_by_date(self):
        self.store.rate("c1", 3)
        self.store.rate("c2", 4)
        rated = self.store.list_rated_content(sort_by="date")
        assert len(rated) == 2

    def test_get_average_rating(self):
        self.store.rate("c1", 3)
        self.store.rate("c2", 5)
        self.store.rate("c3", 4)
        avg = self.store.get_average_rating()
        assert avg == pytest.approx(4.0)

    def test_get_average_rating_empty(self):
        avg = self.store.get_average_rating()
        assert avg == 0.0

    def test_get_rating_distribution(self):
        self.store.rate("c1", 1)
        self.store.rate("c2", 1)
        self.store.rate("c3", 3)
        self.store.rate("c4", 5)
        self.store.rate("c5", 5)
        dist = self.store.get_rating_distribution()
        assert dist[1] == 2
        assert dist[3] == 1
        assert dist[5] == 2

    def test_get_stats(self):
        self.store.rate("c1", 3)
        self.store.rate("c2", 5)
        stats = self.store.get_stats()
        assert isinstance(stats, RatingStats)
        assert stats.total_ratings == 2
        assert stats.average_score == pytest.approx(4.0)

    def test_get_stats_empty(self):
        stats = self.store.get_stats()
        assert stats.total_ratings == 0
        assert stats.average_score == 0.0

    def test_get_rated_by_min_score(self):
        self.store.rate("c1", 3)
        self.store.rate("c2", 5)
        self.store.rate("c3", 2)
        rated = self.store.get_rated_by_min_score(4)
        assert len(rated) == 1
        assert rated[0].score == 5

    def test_get_rated_by_max_score(self):
        self.store.rate("c1", 3)
        self.store.rate("c2", 5)
        self.store.rate("c3", 2)
        rated = self.store.get_rated_by_max_score(3)
        assert len(rated) == 2

    def test_get_rated_by_author(self):
        self.store.rate("c1", 4, author="alice")
        self.store.rate("c2", 5, author="bob")
        self.store.rate("c3", 3, author="alice")
        rated = self.store.get_rated_by_author("alice")
        assert len(rated) == 2

    def test_get_rated_with_comments(self):
        self.store.rate("c1", 4, comment="Good")
        self.store.rate("c2", 5)
        self.store.rate("c3", 3, comment="OK")
        rated = self.store.get_rated_with_comments()
        assert len(rated) == 2

    def test_bulk_rate(self):
        ratings = [("c1", 3), ("c2", 4), ("c3", 5)]
        self.store.bulk_rate(ratings)
        assert self.store.get_rating("c1").score == 3
        assert self.store.get_rating("c2").score == 4
        assert self.store.get_rating("c3").score == 5

    def test_bulk_rate_invalid_skipped(self):
        ratings = [("c1", 3), ("c2", 7), ("c3", 5)]
        self.store.bulk_rate(ratings)
        assert self.store.get_rating("c1").score == 3
        assert self.store.get_rating("c2") is None
        assert self.store.get_rating("c3").score == 5

    def test_clear(self):
        self.store.rate("c1", 4)
        self.store.clear()
        assert self.store.get_rating("c1") is None
        assert self.store.get_stats().total_ratings == 0

    def test_serialize_deserialize(self):
        self.store.rate("c1", 4, comment="Good", author="alice")
        self.store.rate("c2", 3)
        data = self.store.serialize()
        assert len(data) == 2
        new_store = RatingStore()
        new_store.deserialize(data)
        assert new_store.get_rating("c1").score == 4
        assert new_store.get_rating("c2").score == 3
