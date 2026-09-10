"""Adversarial deep tests for content_health.ContentHealthChecker.check_item/check_all
and the `personal-index health` CLI (cli_health.py).

Contract source: personal_index/content_health.py docstrings (check_item runs
up to seven checks in order; status UNHEALTHY on any HIGH/CRITICAL, WARNING on
any MEDIUM or any issue, else HEALTHY; score = checks_passed/checks_total*100,
0.0 when no check ran; check_all defaults missing keys to ""/[]/0.0/200 and
overall_score is the MEAN of per-item scores, 100.0 when empty).
"""

from __future__ import annotations

import json
import os

import pytest

from personal_index.content_health import (
    ContentHealthCheck,
    ContentHealthChecker,
    HealthStatus,
)

GOOD_URL = "http://example.com"  # len 19 > 5
GOOD_TITLE = "Good Title"  # len 10, 3 <= 10 <= 200
GOOD_CONTENT = "x" * 60  # len 60 >= 50


def _checker(**cfg):
    return ContentHealthChecker(config=ContentHealthCheck(**cfg))


def _healthy_item():
    return dict(url=GOOD_URL, title=GOOD_TITLE, content=GOOD_CONTENT,
                tags=[], score=0.0, status_code=200)


# ── check_item: URL check ──────────────────────────────────────────────
class TestCheckItemUrl:
    def test_url_len_5_fails(self):
        r = _checker().check_item(url="abcde", title=GOOD_TITLE, content=GOOD_CONTENT)
        assert any(i.issue_type == "invalid_url" for i in r.issues)

    def test_url_len_6_passes(self):
        r = _checker().check_item(url="abcdef", title=GOOD_TITLE, content=GOOD_CONTENT)
        assert not any(i.issue_type == "invalid_url" for i in r.issues)

    def test_url_empty_fails(self):
        r = _checker().check_item(url="", title=GOOD_TITLE, content=GOOD_CONTENT)
        assert any(i.issue_type == "invalid_url" for i in r.issues)

    def test_url_whitespace_fails(self):
        r = _checker().check_item(url="   ", title=GOOD_TITLE, content=GOOD_CONTENT)
        assert any(i.issue_type == "invalid_url" for i in r.issues)

    def test_url_unicode_passes(self):
        r = _checker().check_item(url="http://éxample.com", title=GOOD_TITLE, content=GOOD_CONTENT)
        assert not any(i.issue_type == "invalid_url" for i in r.issues)


# ── check_item: title presence + length ────────────────────────────────
class TestCheckItemTitle:
    def test_title_len_2_fails_presence(self):
        r = _checker().check_item(url=GOOD_URL, title="ab", content=GOOD_CONTENT)
        assert any(i.issue_type == "missing_title" for i in r.issues)

    def test_title_len_3_passes_presence(self):
        r = _checker().check_item(url=GOOD_URL, title="abc", content=GOOD_CONTENT)
        assert not any(i.issue_type == "missing_title" for i in r.issues)

    def test_title_empty_fails_presence(self):
        r = _checker().check_item(url=GOOD_URL, title="", content=GOOD_CONTENT)
        assert any(i.issue_type == "missing_title" for i in r.issues)

    def test_title_whitespace_passes_presence_len_based(self):
        # Contract: presence passes when title is truthy and len(title) >= min.
        # "   " is truthy with len 3 >= 3, so it passes (len-based, not strip-based).
        r = _checker().check_item(url=GOOD_URL, title="   ", content=GOOD_CONTENT)
        assert not any(i.issue_type == "missing_title" for i in r.issues)

    def test_title_len_200_passes_length(self):
        r = _checker().check_item(url=GOOD_URL, title="a" * 200, content=GOOD_CONTENT)
        assert not any(i.issue_type == "title_too_long" for i in r.issues)

    def test_title_len_201_fails_length(self):
        r = _checker().check_item(url=GOOD_URL, title="a" * 201, content=GOOD_CONTENT)
        assert any(i.issue_type == "title_too_long" for i in r.issues)

    def test_title_unicode_passes(self):
        r = _checker().check_item(url=GOOD_URL, title="Ünïcödé", content=GOOD_CONTENT)
        assert not any(i.issue_type in ("missing_title", "title_too_long") for i in r.issues)


# ── check_item: content length ─────────────────────────────────────────
class TestCheckItemContent:
    def test_content_len_49_fails(self):
        r = _checker().check_item(url=GOOD_URL, title=GOOD_TITLE, content="x" * 49)
        assert any(i.issue_type == "low_content" for i in r.issues)

    def test_content_len_50_passes(self):
        r = _checker().check_item(url=GOOD_URL, title=GOOD_TITLE, content="x" * 50)
        assert not any(i.issue_type == "low_content" for i in r.issues)

    def test_content_empty_fails(self):
        r = _checker().check_item(url=GOOD_URL, title=GOOD_TITLE, content="")
        assert any(i.issue_type == "low_content" for i in r.issues)

    def test_content_unicode_passes(self):
        r = _checker().check_item(url=GOOD_URL, title=GOOD_TITLE, content="é" * 60)
        assert not any(i.issue_type == "low_content" for i in r.issues)


# ── check_item: status code ────────────────────────────────────────────
class TestCheckItemStatus:
    def test_status_199_fails(self):
        r = _checker().check_item(url=GOOD_URL, title=GOOD_TITLE, content=GOOD_CONTENT, status_code=199)
        assert any(i.issue_type == "bad_status" for i in r.issues)

    def test_status_200_passes(self):
        r = _checker().check_item(url=GOOD_URL, title=GOOD_TITLE, content=GOOD_CONTENT, status_code=200)
        assert not any(i.issue_type == "bad_status" for i in r.issues)

    def test_status_399_passes(self):
        r = _checker().check_item(url=GOOD_URL, title=GOOD_TITLE, content=GOOD_CONTENT, status_code=399)
        assert not any(i.issue_type == "bad_status" for i in r.issues)

    def test_status_400_fails(self):
        r = _checker().check_item(url=GOOD_URL, title=GOOD_TITLE, content=GOOD_CONTENT, status_code=400)
        assert any(i.issue_type == "bad_status" for i in r.issues)

    def test_status_0_fails(self):
        r = _checker().check_item(url=GOOD_URL, title=GOOD_TITLE, content=GOOD_CONTENT, status_code=0)
        assert any(i.issue_type == "bad_status" for i in r.issues)


# ── check_item: tags (gated by require_tags) ───────────────────────────
class TestCheckItemTags:
    def test_tags_not_checked_when_require_tags_off(self):
        r = _checker().check_item(url=GOOD_URL, title=GOOD_TITLE, content=GOOD_CONTENT, tags=[])
        assert not any(i.issue_type == "missing_tags" for i in r.issues)
        assert r.checks_total == 5  # url, title_presence, title_length, content, status

    def test_tags_empty_fails_when_required(self):
        r = _checker(require_tags=True).check_item(url=GOOD_URL, title=GOOD_TITLE, content=GOOD_CONTENT, tags=[])
        assert any(i.issue_type == "missing_tags" for i in r.issues)
        assert r.checks_total == 6

    def test_tags_one_passes_when_required(self):
        r = _checker(require_tags=True).check_item(url=GOOD_URL, title=GOOD_TITLE, content=GOOD_CONTENT, tags=["a"])
        assert not any(i.issue_type == "missing_tags" for i in r.issues)

    def test_tags_min_tags_2_boundary(self):
        r = _checker(require_tags=True, min_tags=2).check_item(url=GOOD_URL, title=GOOD_TITLE, content=GOOD_CONTENT, tags=["a"])
        assert any(i.issue_type == "missing_tags" for i in r.issues)
        r2 = _checker(require_tags=True, min_tags=2).check_item(url=GOOD_URL, title=GOOD_TITLE, content=GOOD_CONTENT, tags=["a", "b"])
        assert not any(i.issue_type == "missing_tags" for i in r2.issues)


# ── check_item: score (gated by require_score) ─────────────────────────
class TestCheckItemScore:
    def test_score_not_checked_when_require_score_off(self):
        r = _checker().check_item(url=GOOD_URL, title=GOOD_TITLE, content=GOOD_CONTENT, score=0.0)
        assert not any(i.issue_type == "low_score" for i in r.issues)

    def test_score_below_min_fails_when_required(self):
        r = _checker(require_score=True, min_score=5.0).check_item(url=GOOD_URL, title=GOOD_TITLE, content=GOOD_CONTENT, score=4.9)
        assert any(i.issue_type == "low_score" for i in r.issues)

    def test_score_equal_min_passes_when_required(self):
        r = _checker(require_score=True, min_score=5.0).check_item(url=GOOD_URL, title=GOOD_TITLE, content=GOOD_CONTENT, score=5.0)
        assert not any(i.issue_type == "low_score" for i in r.issues)

    def test_all_seven_checks_run_when_both_required(self):
        r = _checker(require_tags=True, require_score=True).check_item(
            url=GOOD_URL, title=GOOD_TITLE, content=GOOD_CONTENT, tags=["a"], score=5.0, status_code=200)
        assert r.checks_total == 7


# ── status determination ───────────────────────────────────────────────
class TestStatusDetermination:
    def test_all_pass_healthy(self):
        r = _checker().check_item(**_healthy_item())
        assert r.status == HealthStatus.HEALTHY
        assert r.issues == []
        assert r.score == 100.0
        assert r.checks_passed == 5
        assert r.checks_total == 5

    def test_high_issue_unhealthy(self):
        # bad status (HIGH) -> UNHEALTHY even with other MEDIUM issues
        r = _checker().check_item(url=GOOD_URL, title=GOOD_TITLE, content="short", status_code=500)
        assert r.status == HealthStatus.UNHEALTHY

    def test_medium_issue_warning(self):
        # low content (MEDIUM) only -> WARNING
        r = _checker().check_item(url=GOOD_URL, title=GOOD_TITLE, content="short")
        assert r.status == HealthStatus.WARNING

    def test_low_issue_warning(self):
        # title_too_long (LOW) only -> WARNING (any issue at all)
        r = _checker().check_item(url=GOOD_URL, title="a" * 201, content=GOOD_CONTENT)
        assert r.status == HealthStatus.WARNING


# ── score computation ──────────────────────────────────────────────────
class TestScoreComputation:
    def test_score_one_fail(self):
        # 4 of 5 pass -> 80.0
        r = _checker().check_item(url=GOOD_URL, title=GOOD_TITLE, content="short")
        assert r.checks_passed == 4
        assert r.checks_total == 5
        assert r.score == pytest.approx(80.0)

    def test_score_all_fail(self):
        r = _checker().check_item(url="", title="", content="", status_code=500)
        # url fail, title_presence fail, title_length pass (len 0 <= 200), content fail, status fail
        assert r.checks_passed == 1
        assert r.checks_total == 5
        assert r.score == pytest.approx(20.0)


# ── check_all: defaults + aggregation ──────────────────────────────────
class TestCheckAll:
    def test_empty_list(self):
        rep = _checker().check_all([])
        assert rep.total_items == 0
        assert rep.overall_score == 100.0
        assert rep.health_percentage == 100.0

    def test_missing_keys_default(self):
        # only url/title/content present; tags/score/status_code default
        rep = _checker().check_all([{"url": GOOD_URL, "title": GOOD_TITLE, "content": GOOD_CONTENT}])
        assert rep.total_items == 1
        assert rep.healthy_count == 1
        assert rep.results[0].status == HealthStatus.HEALTHY

    def test_overall_score_is_mean(self):
        # item1 healthy (100.0), item2 one fail (80.0) -> mean 90.0
        items = [
            {"url": GOOD_URL, "title": GOOD_TITLE, "content": GOOD_CONTENT},
            {"url": GOOD_URL, "title": GOOD_TITLE, "content": "short"},
        ]
        rep = _checker().check_all(items)
        assert rep.overall_score == pytest.approx(90.0)

    def test_counts_aggregate(self):
        items = [
            {"url": GOOD_URL, "title": GOOD_TITLE, "content": GOOD_CONTENT},  # healthy
            {"url": GOOD_URL, "title": GOOD_TITLE, "content": "short"},       # warning
            {"url": GOOD_URL, "title": GOOD_TITLE, "content": GOOD_CONTENT, "status_code": 500},  # unhealthy
        ]
        rep = _checker().check_all(items)
        assert rep.healthy_count == 1
        assert rep.warning_count == 1
        assert rep.unhealthy_count == 1
        assert rep.total_items == 3

    def test_idempotence(self):
        items = [{"url": GOOD_URL, "title": GOOD_TITLE, "content": GOOD_CONTENT}]
        r1 = _checker().check_all(items)
        r2 = _checker().check_all(items)
        assert r1.overall_score == r2.overall_score
        assert r1.total_items == r2.total_items


# ── CLI end-to-end (installed `personal-index health`) ─────────────────
class TestCliHealthEndToEnd:
    def _write(self, dd, pages, page_tags=None):
        os.makedirs(dd, exist_ok=True)
        with open(os.path.join(dd, "search_index.json"), "w") as f:
            json.dump({"pages": pages, "word_index": {}}, f)
        with open(os.path.join(dd, "tags.json"), "w") as f:
            json.dump({"tags": {}, "page_tags": page_tags or {}}, f)

    def _run(self, dd):
        from click.testing import CliRunner
        from personal_index.cli import main
        return CliRunner().invoke(main, ["health", "--data-dir", dd])

    def test_healthy_content(self, tmp_path):
        dd = str(tmp_path / "data")
        self._write(dd, {"http://example.com": {
            "url": "http://example.com", "title": "Good Title",
            "content": "x" * 60, "score": 1.0, "status_code": 200}})
        res = self._run(dd)
        assert res.exit_code == 0, res.output
        assert "All content is healthy" in res.output

    def test_unhealthy_content_reports_issues(self, tmp_path):
        dd = str(tmp_path / "data")
        self._write(dd, {"http://example.com": {
            "url": "http://example.com", "title": "T",
            "content": "short", "score": 1.0, "status_code": 500}})
        res = self._run(dd)
        assert res.exit_code == 0, res.output
        assert "Issues Found" in res.output

    def test_empty_index(self, tmp_path):
        dd = str(tmp_path / "data")
        self._write(dd, {})
        res = self._run(dd)
        assert res.exit_code == 0, res.output
        assert "No indexed content found" in res.output


# ── DEFECT (QA-26): None title/content crash ───────────────────────────
# Root cause: _check_title_length (content_health.py:240) and
# _check_content_length (content_health.py:255) call len(title)/len(content)
# unguarded. _check_title_presence (line 225) guards with `title and ...` so it
# passes None through as falsy, but the subsequent _check_title_length then
# calls len(None) -> TypeError. Reachable via the public `health` CLI (a page
# in search_index.json with "title": null; the CLI coerces content but NOT
# title) and via the public check_item/check_all API.
class TestNoneFieldDefect:
    @pytest.mark.xfail(
        strict=True,
        reason="QA-26: check_item crashes (TypeError) on title=None; "
               "_check_title_length calls len(title) unguarded",
    )
    def test_check_item_none_title(self):
        r = _checker().check_item(url=GOOD_URL, title=None, content=GOOD_CONTENT)
        assert r.status in (HealthStatus.HEALTHY, HealthStatus.WARNING, HealthStatus.UNHEALTHY)

    @pytest.mark.xfail(
        strict=True,
        reason="QA-26: check_item crashes (TypeError) on content=None; "
               "_check_content_length calls len(content) unguarded",
    )
    def test_check_item_none_content(self):
        r = _checker().check_item(url=GOOD_URL, title=GOOD_TITLE, content=None)
        assert r.status in (HealthStatus.HEALTHY, HealthStatus.WARNING, HealthStatus.UNHEALTHY)

    @pytest.mark.xfail(
        strict=True,
        reason="QA-26: check_all crashes (TypeError) on a present-but-None "
               "title key; _check_title_length calls len(title) unguarded",
    )
    def test_check_all_none_title_key(self):
        rep = _checker().check_all([{"url": GOOD_URL, "title": None, "content": GOOD_CONTENT}])
        assert rep.total_items == 1

    @pytest.mark.xfail(
        strict=True,
        reason="QA-26: `personal-index health` crashes (TypeError) when a page "
               "in search_index.json has \"title\": null; the CLI coerces "
               "content (page.content or \"\") but NOT title, violating the "
               "defensive-load contract (ARCH-63)",
    )
    def test_cli_health_null_title_page(self, tmp_path):
        from click.testing import CliRunner
        from personal_index.cli import main
        dd = str(tmp_path / "data")
        os.makedirs(dd, exist_ok=True)
        with open(os.path.join(dd, "search_index.json"), "w") as f:
            json.dump({"pages": {"http://example.com": {
                "url": "http://example.com", "title": None,
                "content": "x" * 60, "score": 1.0, "status_code": 200}},
                "word_index": {}}, f)
        with open(os.path.join(dd, "tags.json"), "w") as f:
            json.dump({"tags": {}, "page_tags": {}}, f)
        res = CliRunner().invoke(main, ["health", "--data-dir", dd])
        assert res.exit_code == 0, res.output
