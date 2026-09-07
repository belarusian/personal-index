"""Adversarial deep tests for content_health.HealthReport.summary / health_percentage.

Contract source: personal_index/content_health.py docstring (exact contract
merged via #934). Pins the documented 8-line summary format, the zero-total
guard (health_percentage -> 100.0), and the percent/score rendering.
"""

from __future__ import annotations

from personal_index.content_health import HealthReport


def _report(total=0, healthy=0, warning=0, unhealthy=0, score=100.0):
    return HealthReport(
        total_items=total,
        healthy_count=healthy,
        warning_count=warning,
        unhealthy_count=unhealthy,
        overall_score=score,
    )


def test_zero_total_summary_exact_lines():
    """total_items=0 -> health_percentage renders 100.0%."""
    lines = _report().summary().split("\n")
    assert lines[0] == "Content Health Report"
    assert lines[1] == "=" * 40
    assert lines[2] == "Total items: 0"
    assert lines[3] == "Healthy: 0"
    assert lines[4] == "Warnings: 0"
    assert lines[5] == "Unhealthy: 0"
    assert lines[6] == "Overall score: 100.0/100"
    assert lines[7] == "Health percentage: 100.0%"
    assert len(lines) == 8


def test_summary_line_count_and_order():
    r = _report(total=10, healthy=8, warning=1, unhealthy=1, score=80.0)
    lines = r.summary().split("\n")
    assert len(lines) == 8
    assert lines[2] == "Total items: 10"
    assert lines[3] == "Healthy: 8"
    assert lines[4] == "Warnings: 1"
    assert lines[5] == "Unhealthy: 1"
    assert lines[6] == "Overall score: 80.0/100"


def test_health_percentage_zero_total_guard():
    assert _report(total=0, healthy=0).health_percentage == 100.0


def test_health_percentage_normal():
    assert _report(total=4, healthy=3).health_percentage == 75.0


def test_health_percentage_all_healthy():
    assert _report(total=5, healthy=5).health_percentage == 100.0


def test_health_percentage_none_healthy():
    assert _report(total=5, healthy=0).health_percentage == 0.0


def test_health_percentage_rendering_in_summary():
    r = _report(total=3, healthy=1, score=33.3)
    # 1/3 = 33.333... -> "33.3%"
    assert "Health percentage: 33.3%" in r.summary()
    assert "Overall score: 33.3/100" in r.summary()


def test_summary_idempotence():
    r = _report(total=6, healthy=4, warning=1, unhealthy=1, score=66.6)
    assert r.summary() == r.summary()


def test_score_one_decimal_rendering():
    r = _report(total=1, healthy=1, score=99.99)
    # 99.99 -> "100.0" with .1f
    assert "Overall score: 100.0/100" in r.summary()
