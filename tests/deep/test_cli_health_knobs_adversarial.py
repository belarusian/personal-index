"""Adversarial deep tests for the `personal-index health` CLI knob pass-through.

Contract source: ARCH-101 (issue #1499) — the `health` command must expose all
seven ContentHealthCheck knobs, specifically `--max-title-length` (gates the
`title_too_long` check) and `--min-tags` (gates the `missing_tags` check, only
active with `--require-tags`). The implementer's pinning test
(tests/test_cli_health.py) covers the happy path; this file attacks the
pass-through with edge values: zero, negative, boundary, unicode, and
idempotence, plus an end-to-end CLI run.

The checker contract (content_health.py docstrings):
  - title_too_long fires when len(title) > max_title_length (LOW severity).
  - missing_tags fires ONLY when require_tags is set AND (tags falsy OR
    len(tags) < min_tags) (LOW severity).
  - A LOW-only issue set -> WARNING status.
"""

from __future__ import annotations

import json
import os

from click.testing import CliRunner
from personal_index.cli import main


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


# ── --max-title-length pass-through ────────────────────────────────────
class TestMaxTitleLengthKnob:
    def test_long_title_flagged_when_knob_lowered(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, _page(title="A" * 20))  # len 20
        res = _run(dd, "--max-title-length", "10")
        assert res.exit_code == 0, res.output
        assert "title_too_long" in res.output or "exceeds 10 characters" in res.output

    def test_default_max_title_length_no_issue(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, _page(title="A" * 20))  # len 20 <= default 200
        res = _run(dd)
        assert res.exit_code == 0, res.output
        assert "title_too_long" not in res.output

    def test_boundary_title_exactly_max_passes(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, _page(title="B" * 15))  # len 15 == max 15 -> passes (<=)
        res = _run(dd, "--max-title-length", "15")
        assert res.exit_code == 0, res.output
        assert "title_too_long" not in res.output

    def test_boundary_title_one_over_max_fails(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, _page(title="B" * 16))  # len 16 > max 15 -> fails
        res = _run(dd, "--max-title-length", "15")
        assert res.exit_code == 0, res.output
        assert "title_too_long" in res.output or "exceeds 15 characters" in res.output

    def test_zero_max_title_length_flags_any_nonempty_title(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, _page(title="T"))  # len 1 > 0 -> title_too_long
        res = _run(dd, "--max-title-length", "0")
        assert res.exit_code == 0, res.output
        assert "title_too_long" in res.output or "exceeds 0 characters" in res.output

    def test_negative_max_title_length_flags_any_nonempty_title(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, _page(title="T"))  # len 1 > -5 -> title_too_long
        res = _run(dd, "--max-title-length", "-5")
        assert res.exit_code == 0, res.output
        assert "title_too_long" in res.output or "exceeds -5 characters" in res.output

    def test_large_max_title_length_never_flags(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, _page(title="C" * 5000))  # len 5000 <= 10000
        res = _run(dd, "--max-title-length", "10000")
        assert res.exit_code == 0, res.output
        assert "title_too_long" not in res.output

    def test_unicode_title_length_counts_codepoints(self, tmp_path):
        dd = str(tmp_path / "d")
        # 10 codepoints (emoji count as 1 each for len())
        _write(dd, _page(title="é" * 10))
        res = _run(dd, "--max-title-length", "9")
        assert res.exit_code == 0, res.output
        assert "title_too_long" in res.output or "exceeds 9 characters" in res.output


# ── --min-tags pass-through (requires --require-tags) ──────────────────
class TestMinTagsKnob:
    def test_single_tag_flagged_when_min_tags_2(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, _page(), page_tags={"http://example.com": ["one"]})
        res = _run(dd, "--require-tags", "--min-tags", "2")
        assert res.exit_code == 0, res.output
        assert "missing_tags" in res.output or "min 2 required" in res.output

    def test_default_min_tags_single_tag_passes(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, _page(), page_tags={"http://example.com": ["one"]})
        res = _run(dd, "--require-tags")  # default min_tags 1
        assert res.exit_code == 0, res.output
        assert "missing_tags" not in res.output

    def test_boundary_tags_exactly_min_passes(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, _page(), page_tags={"http://example.com": ["a", "b"]})
        res = _run(dd, "--require-tags", "--min-tags", "2")
        assert res.exit_code == 0, res.output
        assert "missing_tags" not in res.output

    def test_boundary_tags_one_under_min_fails(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, _page(), page_tags={"http://example.com": ["a"]})
        res = _run(dd, "--require-tags", "--min-tags", "2")
        assert res.exit_code == 0, res.output
        assert "missing_tags" in res.output or "min 2 required" in res.output

    def test_min_tags_not_active_without_require_tags(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, _page())  # no tags at all
        res = _run(dd, "--min-tags", "5")  # no --require-tags
        assert res.exit_code == 0, res.output
        assert "missing_tags" not in res.output

    def test_zero_min_tags_with_one_tag_passes(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, _page(), page_tags={"http://example.com": ["one"]})
        res = _run(dd, "--require-tags", "--min-tags", "0")
        assert res.exit_code == 0, res.output
        assert "missing_tags" not in res.output

    def test_zero_min_tags_with_no_tags_still_fails(self, tmp_path):
        # Contract: missing_tags fires when tags is FALSY regardless of
        # min_tags (the `tags and len(tags) >= min_tags` guard).
        dd = str(tmp_path / "d")
        _write(dd, _page())  # no tags
        res = _run(dd, "--require-tags", "--min-tags", "0")
        assert res.exit_code == 0, res.output
        assert "missing_tags" in res.output or "min 0 required" in res.output

    def test_negative_min_tags_with_one_tag_passes(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, _page(), page_tags={"http://example.com": ["one"]})
        res = _run(dd, "--require-tags", "--min-tags", "-3")
        assert res.exit_code == 0, res.output
        assert "missing_tags" not in res.output


# ── idempotence + end-to-end ───────────────────────────────────────────
class TestIdempotenceAndE2E:
    def test_health_is_idempotent(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, _page(title="A" * 20), page_tags={"http://example.com": ["one"]})
        r1 = _run(dd, "--max-title-length", "10", "--require-tags", "--min-tags", "2")
        r2 = _run(dd, "--max-title-length", "10", "--require-tags", "--min-tags", "2")
        assert r1.exit_code == 0 and r2.exit_code == 0
        assert r1.output == r2.output

    def test_end_to_end_cli_run_healthy(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, _page())
        res = _run(dd, "--max-title-length", "200", "--min-tags", "1")
        assert res.exit_code == 0, res.output
        assert "All content is healthy" in res.output

    def test_end_to_end_cli_run_reports_issue_count(self, tmp_path):
        dd = str(tmp_path / "d")
        _write(dd, _page(title="A" * 20), page_tags={"http://example.com": []})
        res = _run(dd, "--max-title-length", "10", "--require-tags", "--min-tags", "2")
        assert res.exit_code == 0, res.output
        assert "Issues Found" in res.output
