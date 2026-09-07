"""Adversarial deep tests for content_dedup.DedupResult.summary / dedup_ratio.

Contract source: personal_index/content_dedup.py docstring (exact contract
merged via #920). Pins the documented 7-line summary format, the percent
rendering of dedup_ratio, and the zero-total guard.
"""

from __future__ import annotations

from personal_index.content_dedup import DedupResult


def _result(total=0, unique=0, removed=0, groups=0, method="hash"):
    return DedupResult(
        total_items=total,
        unique_items=unique,
        duplicate_groups=[],
        removed_count=removed,
        method=method,
    )


def test_zero_total_summary_exact_lines():
    """total_items=0 -> ratio line '0.0%', numeric fields 0."""
    s = _result().summary()
    lines = s.split("\n")
    assert lines[0] == "Deduplication Results:"
    assert lines[1] == "  Total items: 0"
    assert lines[2] == "  Unique items: 0"
    assert lines[3] == "  Duplicates found: 0"
    assert lines[4] == "  Duplicate groups: 0"
    assert lines[5] == "  Dedup ratio: 0.0%"
    assert lines[6] == "  Method: hash"
    assert len(lines) == 7


def test_summary_line_order_and_count():
    r = _result(total=10, unique=7, removed=3, method="url")
    lines = r.summary().split("\n")
    assert len(lines) == 7
    assert lines[1] == "  Total items: 10"
    assert lines[2] == "  Unique items: 7"
    assert lines[3] == "  Duplicates found: 3"
    assert lines[4] == "  Duplicate groups: 0"
    assert lines[6] == "  Method: url"


def test_dedup_ratio_percent_rendering():
    r = _result(total=10, removed=3)
    # 3/10 = 0.3 -> "30.0%"
    assert "  Dedup ratio: 30.0%" in r.summary()


def test_dedup_ratio_half():
    r = _result(total=2, removed=1)
    assert "  Dedup ratio: 50.0%" in r.summary()


def test_dedup_ratio_all_duplicates():
    r = _result(total=5, removed=5)
    assert "  Dedup ratio: 100.0%" in r.summary()


def test_dedup_ratio_property_zero_total():
    assert _result(total=0, removed=0).dedup_ratio == 0.0


def test_dedup_ratio_property_normal():
    assert _result(total=4, removed=1).dedup_ratio == 0.25


def test_summary_idempotence():
    r = _result(total=8, unique=5, removed=3)
    assert r.summary() == r.summary()


def test_summary_unicode_method():
    """method is rendered verbatim; unicode method string survives."""
    r = _result(total=1, removed=0, method="similarity-日本語")
    assert "  Method: similarity-日本語" in r.summary()


def test_duplicate_groups_count_reflected():
    r = _result(total=10, unique=8, removed=2)
    r.duplicate_groups = [object(), object()]  # type: ignore[assignment]
    assert "  Duplicate groups: 2" in r.summary()
