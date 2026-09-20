"""Adversarial deep tests for personal_index.cli_health (the LIVE `health` command).

This is the ONLY module in personal_index/ with no deep test importing it
directly (the existing test_cli_health_knobs_adversarial.py drives it only via
`cli.main` for two knobs). This file attacks the module's OWN private helpers
(`_build_config`, `_build_health_items`, `_severity_icon`, `_print_report`)
plus the full `health` command end-to-end with edge values: None / empty /
whitespace / unicode / negative / out-of-range, idempotence, and the
require_score derivation invariant.

Contract sources:
  - docs/cli_health.md (spec for cli_health.py helpers + invariants)
  - docs/content-health.md (the checker contract the command drives)
  - content_health.py docstrings (check_item 7-check contract)

Key invariants pinned here:
  - `_build_config` sets ALL seven ContentHealthCheck fields (post-ARCH-101);
    `require_score` is DERIVED as `min_score > 0` (not a flag).
  - `_build_health_items` maps title/content None -> "", defaults a missing
    status_code attr to 200, and pulls tags from the tag store.
  - `_severity_icon` maps the four severities and falls back to the neutral
    icon for anything else (unknown / empty / None / unicode).
  - `_print_report` prints the "healthy" line only when total_issues == 0.
"""

from __future__ import annotations

import json
import os
from types import SimpleNamespace

from click.testing import CliRunner
from personal_index.cli import main
from personal_index.cli_health import (
    _build_config,
    _build_health_items,
    _print_report,
    _severity_icon,
)
from personal_index.content_health import (
    ContentHealthChecker,
    HealthReport,
)


# ── helpers ────────────────────────────────────────────────────────────
def _write(dd, pages, page_tags=None):
    os.makedirs(dd, exist_ok=True)
    with open(os.path.join(dd, "search_index.json"), "w") as f:
        json.dump({"pages": pages, "word_index": {}}, f)
    with open(os.path.join(dd, "tags.json"), "w") as f:
        json.dump({"tags": {}, "page_tags": page_tags or {}}, f)


def _run(dd, *args):
    return CliRunner().invoke(main, ["health", "--data-dir", dd, *args])


def _page(url="http://example.com", title="Good Title", content="x" * 60,
          score=1.0, status_code=200):
    return {url: {"url": url, "title": title, "content": content,
                  "score": score, "status_code": status_code}}


class _StubTagStore:
    """Minimal stand-in for TagStore: get_tags_for_url -> list of str."""

    def __init__(self, mapping=None):
        self._m = mapping or {}

    def get_tags_for_url(self, url):
        return list(self._m.get(url, []))


# ── _build_config: all seven knobs + require_score derivation ─────────
class TestBuildConfig:
    def test_all_seven_fields_set(self):
        cfg = _build_config(10, 2, True, 0.5, 50, 3)
        assert cfg.min_content_length == 10
        assert cfg.min_title_length == 2
        assert cfg.max_title_length == 50
        assert cfg.require_tags is True
        assert cfg.min_tags == 3
        assert cfg.require_score is True
        assert cfg.min_score == 0.5

    def test_require_score_derived_not_flag(self):
        # min_score > 0 -> require_score True
        assert _build_config(50, 3, False, 0.1, 200, 1).require_score is True
        # min_score == 0.0 (default) -> require_score False (score check off)
        assert _build_config(50, 3, False, 0.0, 200, 1).require_score is False
        # negative min_score -> require_score False (0 > 0 is False)
        assert _build_config(50, 3, False, -1.0, 200, 1).require_score is False

    def test_min_score_value_preserved_even_when_require_off(self):
        cfg = _build_config(50, 3, False, 0.0, 200, 1)
        assert cfg.min_score == 0.0
        assert cfg.require_score is False

    def test_zero_and_negative_knobs_pass_through(self):
        cfg = _build_config(0, 0, False, 0.0, 0, 0)
        assert cfg.min_content_length == 0
        assert cfg.min_title_length == 0
        assert cfg.max_title_length == 0
        assert cfg.min_tags == 0

    def test_unicode_agnostic_int_knobs(self):
        # int knobs are ints; a large value passes through unchanged
        cfg = _build_config(10**9, 3, False, 0.0, 10**9, 1)
        assert cfg.min_content_length == 10**9
        assert cfg.max_title_length == 10**9


# ── _build_health_items: field mapping + None/attr defaults ───────────
class TestBuildHealthItems:
    def test_full_page_mapped(self):
        page = SimpleNamespace(url="http://a.com", title="T", content="c" * 60,
                               score=0.7, status_code=200)
        items = _build_health_items([page], _StubTagStore({"http://a.com": ["x", "y"]}))
        assert items == [{
            "url": "http://a.com", "title": "T", "content": "c" * 60,
            "tags": ["x", "y"], "score": 0.7, "status_code": 200,
        }]

    def test_none_title_and_content_become_empty_string(self):
        page = SimpleNamespace(url="http://a.com", title=None, content=None,
                               score=0.0, status_code=200)
        items = _build_health_items([page], _StubTagStore())
        assert items[0]["title"] == ""
        assert items[0]["content"] == ""

    def test_missing_status_code_attr_defaults_to_200(self):
        page = SimpleNamespace(url="http://a.com", title="T", content="c" * 60,
                               score=0.0)  # no status_code attribute
        items = _build_health_items([page], _StubTagStore())
        assert items[0]["status_code"] == 200

    def test_explicit_status_code_preserved(self):
        page = SimpleNamespace(url="http://a.com", title="T", content="c" * 60,
                               score=0.0, status_code=404)
        items = _build_health_items([page], _StubTagStore())
        assert items[0]["status_code"] == 404

    def test_tags_pulled_from_store(self):
        page = SimpleNamespace(url="http://a.com", title="T", content="c" * 60,
                               score=0.0, status_code=200)
        items = _build_health_items([page], _StubTagStore({"http://a.com": ["a", "b", "c"]}))
        assert items[0]["tags"] == ["a", "b", "c"]

    def test_unlisted_url_gets_empty_tags(self):
        page = SimpleNamespace(url="http://a.com", title="T", content="c" * 60,
                               score=0.0, status_code=200)
        items = _build_health_items([page], _StubTagStore())
        assert items[0]["tags"] == []

    def test_empty_pages_returns_empty_list(self):
        assert _build_health_items([], _StubTagStore()) == []

    def test_multiple_pages_preserve_order(self):
        pages = [
            SimpleNamespace(url="http://1.com", title="A", content="c" * 60, score=0.1, status_code=200),
            SimpleNamespace(url="http://2.com", title="B", content="c" * 60, score=0.2, status_code=200),
        ]
        items = _build_health_items(pages, _StubTagStore())
        assert [i["url"] for i in items] == ["http://1.com", "http://2.com"]

    def test_unicode_fields_round_trip(self):
        page = SimpleNamespace(url="http://ünïcode.com", title="标题",
                               content="内容" * 30, score=0.5, status_code=200)
        items = _build_health_items([page], _StubTagStore())
        assert items[0]["url"] == "http://ünïcode.com"
        assert items[0]["title"] == "标题"


# ── _severity_icon: four severities + fallback ────────────────────────
class TestSeverityIcon:
    def test_critical(self):
        assert _severity_icon("critical") == "🔴"

    def test_high(self):
        assert _severity_icon("high") == "🟠"

    def test_medium(self):
        assert _severity_icon("medium") == "🟡"

    def test_low(self):
        assert _severity_icon("low") == "🔵"

    def test_unknown_string_falls_back_to_neutral(self):
        assert _severity_icon("bogus") == "⚪"

    def test_empty_string_falls_back_to_neutral(self):
        assert _severity_icon("") == "⚪"

    def test_none_falls_back_to_neutral(self):
        assert _severity_icon(None) == "⚪"

    def test_unicode_severity_falls_back_to_neutral(self):
        assert _severity_icon("严重") == "⚪"

    def test_case_sensitive(self):
        # the map keys are lowercase; "HIGH" is not a key -> neutral
        assert _severity_icon("HIGH") == "⚪"


# ── _print_report: healthy vs issues ──────────────────────────────────
class TestPrintReport:
    def test_zero_issues_prints_healthy_line(self, capsys):
        report = HealthReport(total_items=1, healthy_count=1, warning_count=0,
                              unhealthy_count=0, unknown_count=0, total_issues=0,
                              results=[], overall_score=100.0)
        _print_report(report)
        out = capsys.readouterr().out
        assert "✓ All content is healthy!" in out
        assert "Issues Found" not in out

    def test_with_issues_prints_issues_header(self, capsys):
        report = HealthReport(total_items=1, healthy_count=0, warning_count=1,
                              unhealthy_count=0, unknown_count=0, total_issues=2,
                              results=[], overall_score=50.0)
        _print_report(report)
        out = capsys.readouterr().out
        assert "Issues Found (2):" in out
        assert "✓ All content is healthy!" not in out

    def test_summary_header_always_printed(self, capsys):
        report = HealthReport(total_items=0, healthy_count=0, warning_count=0,
                              unhealthy_count=0, unknown_count=0, total_issues=0,
                              results=[], overall_score=100.0)
        _print_report(report)
        out = capsys.readouterr().out
        assert "Content Health Report" in out


# ── `health` command end-to-end ───────────────────────────────────────
class TestHealthCommandE2E:
    def test_empty_index_guard(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, {})
        res = _run(dd)
        assert res.exit_code == 0, res.output
        assert "No indexed content found" in res.output

    def test_healthy_page_reports_healthy(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, _page())
        res = _run(dd)
        assert res.exit_code == 0, res.output
        assert "✓ All content is healthy!" in res.output

    def test_bad_status_code_reports_unhealthy(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, _page(status_code=404))
        res = _run(dd)
        assert res.exit_code == 0, res.output
        assert "bad_status" in res.output or "404" in res.output

    def test_negative_min_content_length_does_not_crash(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, _page())
        res = _run(dd, "--min-content-length", "-5")
        assert res.exit_code == 0, res.output

    def test_negative_max_title_length_does_not_crash(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, _page())
        res = _run(dd, "--max-title-length", "-1")
        assert res.exit_code == 0, res.output

    def test_negative_min_tags_does_not_crash(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, _page())
        res = _run(dd, "--min-tags", "-3", "--require-tags")
        assert res.exit_code == 0, res.output

    def test_negative_min_score_does_not_crash(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, _page())
        res = _run(dd, "--min-score", "-0.5")
        assert res.exit_code == 0, res.output

    def test_unicode_page_does_not_crash(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, _page(url="http://ünïcode.com", title="标题", content="内容" * 30))
        res = _run(dd)
        assert res.exit_code == 0, res.output

    def test_idempotent_two_runs_same_output(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, _page())
        r1 = _run(dd)
        r2 = _run(dd)
        assert r1.output == r2.output
        assert r1.exit_code == r2.exit_code == 0


# ── URL length boundary (contract: len(url) > 5, docs/content-health.md:151) ─
# The boundary is EXACTLY at len(url) == 5: len 4 and len 5 are REJECTED
# (invalid_url), len 6 is ACCEPTED. Pinned to document the exact boundary.
class TestUrlLengthBoundary:
    def test_len4_url_rejected(self):
        # len 4: 4 > 5 False -> invalid_url.
        r = ContentHealthChecker().check_item(url="abcd", title="Good Title",
                                              content="x" * 60)
        assert any(i.issue_type == "invalid_url" for i in r.issues)

    def test_len5_url_rejected(self):
        # len 5: 5 > 5 False -> invalid_url (the exact boundary).
        r = ContentHealthChecker().check_item(url="abcde", title="Good Title",
                                              content="x" * 60)
        assert any(i.issue_type == "invalid_url" for i in r.issues)

    def test_len6_url_accepted(self):
        # len 6: 6 > 5 True -> valid.
        r = ContentHealthChecker().check_item(url="abcdef", title="Good Title",
                                              content="x" * 60)
        assert not any(i.issue_type == "invalid_url" for i in r.issues)

    def test_empty_url_rejected(self):
        # empty: falsy -> invalid_url.
        r = ContentHealthChecker().check_item(url="", title="Good Title",
                                              content="x" * 60)
        assert any(i.issue_type == "invalid_url" for i in r.issues)

    def test_len5_url_flagged_via_health_command(self, tmp_path):
        # end-to-end: a 5-char URL page is flagged invalid_url by the command.
        dd = str(tmp_path / "d")
        _write(dd, _page(url="abcde"))
        res = _run(dd)
        assert res.exit_code == 0, res.output
        # _print_issues prints issue.message (not issue_type); the invalid_url
        # message is "URL is missing or too short".
        assert "URL is missing or too short" in res.output
