"""Adversarial deep tests for content_scoring.ContentScorer._build_score.

Contract source: personal_index/content_scoring.py docstring (exact contract
merged via #973). Pins: each of the seven numeric fields is round(x, 4); the
factors dict holds the UNROUNDED inputs and is keyed by the six factor names
(NOT total).
"""

from __future__ import annotations

from personal_index.content_scoring import ContentScorer


def _scorer() -> ContentScorer:
    return ContentScorer()


def test_fields_rounded_to_4_places():
    s = _scorer()
    cs = s._build_score(
        total=0.123456789, recency=0.987654321, relevance=0.555555555,
        engagement=0.333333333, quality=0.222222222,
        authority=0.111111111, freshness=0.777777777,
    )
    assert cs.total == round(0.123456789, 4)
    assert cs.recency == round(0.987654321, 4)
    assert cs.relevance == round(0.555555555, 4)
    assert cs.engagement == round(0.333333333, 4)
    assert cs.quality == round(0.222222222, 4)
    assert cs.authority == round(0.111111111, 4)
    assert cs.freshness == round(0.777777777, 4)


def test_factors_dict_unrounded():
    s = _scorer()
    raw = dict(recency=0.987654321, relevance=0.555555555, engagement=0.333333333,
               quality=0.222222222, authority=0.111111111, freshness=0.777777777)
    cs = s._build_score(total=0.5, **raw)
    for k, v in raw.items():
        assert cs.factors[k] == v  # exact, unrounded


def test_factors_dict_keys_exactly_six_no_total():
    s = _scorer()
    cs = s._build_score(total=0.5, recency=0.1, relevance=0.2, engagement=0.3,
                        quality=0.4, authority=0.5, freshness=0.6)
    assert set(cs.factors.keys()) == {
        "recency", "relevance", "engagement", "quality", "authority", "freshness"
    }
    assert "total" not in cs.factors


def test_zero_inputs():
    s = _scorer()
    cs = s._build_score(total=0.0, recency=0.0, relevance=0.0, engagement=0.0,
                        quality=0.0, authority=0.0, freshness=0.0)
    assert cs.total == 0.0
    assert all(cs.factors[k] == 0.0 for k in cs.factors)


def test_one_inputs():
    s = _scorer()
    cs = s._build_score(total=1.0, recency=1.0, relevance=1.0, engagement=1.0,
                        quality=1.0, authority=1.0, freshness=1.0)
    assert cs.total == 1.0
    assert all(cs.factors[k] == 1.0 for k in cs.factors)


def test_idempotence():
    s = _scorer()
    a = s._build_score(total=0.12345, recency=0.2, relevance=0.3, engagement=0.4,
                       quality=0.5, authority=0.6, freshness=0.7)
    b = s._build_score(total=0.12345, recency=0.2, relevance=0.3, engagement=0.4,
                       quality=0.5, authority=0.6, freshness=0.7)
    assert a.total == b.total
    assert a.factors == b.factors
