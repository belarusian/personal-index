"""Adversarial PROBE tests for publish_dashboard (cycle 208).

publish_dashboard is a standalone CLI (has __main__, not a cli.py subcommand)
with NO docs page - a defect magnet. The core logic is validate_sync, which
compares the JSON codemap summary against the HTML-embedded metadata summary.

Contract (docstring): "Validate that HTML embedded metadata and JSON codemap
are in sync." The generator writes both from the same metadata object, so the
reachable inputs are well-formed; these tests probe the guard paths and the
escape round-trip (QA-32/QA-33 class) plus the one-sided comparison.
"""

from __future__ import annotations

import html as htmlmod
import json
from pathlib import Path

import pytest

from personal_index.publish_dashboard import validate_sync

TAG = '<script type="application/json" id="codemap-metadata">'


def _make_html(summary: dict) -> str:
    """Build a minimal HTML doc embedding ``summary`` the way the generator does."""
    payload = json.dumps({"summary": summary})
    return f"<html><body>{TAG}{htmlmod.escape(payload)}</script></body></html>"


def _make_json(summary: dict) -> dict:
    return {"summary": summary}


def _write(tmp_path: Path, html: str, codemap: dict) -> tuple[Path, Path]:
    hp = tmp_path / "dash.html"
    jp = tmp_path / "codemap.json"
    hp.write_text(html, encoding="utf-8")
    jp.write_text(json.dumps(codemap), encoding="utf-8")
    return hp, jp


class TestValidateSyncInSync:
    def test_identical_summaries_sync(self, tmp_path):
        s = {"total_modules": 5, "total_lines": 100, "total_errors": 0, "total_warnings": 2}
        hp, jp = _write(tmp_path, _make_html(s), _make_json(s))
        r = validate_sync(hp, jp)
        assert r["sync"] is True
        assert r["summary"] == s

    def test_round_trip_escape_is_lossless(self, tmp_path):
        """The escape path: a summary value containing HTML special chars must
        survive the escape -> unescape round-trip exactly once (QA-32/QA-33 class)."""
        s = {"total_modules": 1, "total_lines": 2, "total_errors": 0, "total_warnings": 0}
        s["note"] = 'a <b> & "c" \'d\''
        hp, jp = _write(tmp_path, _make_html(s), _make_json(s))
        r = validate_sync(hp, jp)
        assert r["sync"] is True
        assert r["summary"]["note"] == 'a <b> & "c" \'d\''

    def test_unicode_summary_sync(self, tmp_path):
        s = {"total_modules": 3, "total_lines": 42, "total_errors": 0, "total_warnings": 0}
        s["label"] = "спасіба дзенница"
        hp, jp = _write(tmp_path, _make_html(s), _make_json(s))
        r = validate_sync(hp, jp)
        assert r["sync"] is True
        assert r["summary"]["label"] == "спасіба дзенница"


class TestValidateSyncOutOfSync:
    def test_value_mismatch_detected(self, tmp_path):
        s_json = {"total_modules": 5, "total_lines": 100, "total_errors": 0, "total_warnings": 2}
        s_html = {"total_modules": 6, "total_lines": 100, "total_errors": 0, "total_warnings": 2}
        hp, jp = _write(tmp_path, _make_html(s_html), _make_json(s_json))
        r = validate_sync(hp, jp)
        assert r["sync"] is False
        assert any("total_modules" in m for m in r["mismatches"])

    def test_json_key_missing_in_html_detected(self, tmp_path):
        """A key present in JSON but absent in HTML -> mismatch (get -> None)."""
        s_json = {"total_modules": 5, "total_lines": 100, "total_errors": 0, "total_warnings": 2}
        s_html = {"total_modules": 5, "total_lines": 100, "total_errors": 0}
        hp, jp = _write(tmp_path, _make_html(s_html), _make_json(s_json))
        r = validate_sync(hp, jp)
        assert r["sync"] is False
        assert any("total_warnings" in m for m in r["mismatches"])


class TestValidateSyncGuardPaths:
    def test_codemap_not_object(self, tmp_path):
        hp = tmp_path / "dash.html"
        hp.write_text(_make_html({"total_modules": 1}), encoding="utf-8")
        jp = tmp_path / "codemap.json"
        jp.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        r = validate_sync(hp, jp)
        assert r["sync"] is False
        assert "not an object" in r["reason"]

    def test_no_embedded_metadata(self, tmp_path):
        hp = tmp_path / "dash.html"
        hp.write_text("<html><body>no metadata here</body></html>", encoding="utf-8")
        jp = tmp_path / "codemap.json"
        jp.write_text(json.dumps(_make_json({"total_modules": 1})), encoding="utf-8")
        r = validate_sync(hp, jp)
        assert r["sync"] is False
        assert "no embedded metadata" in r["reason"]

    def test_embedded_not_object(self, tmp_path):
        hp = tmp_path / "dash.html"
        payload = json.dumps([1, 2, 3])
        hp.write_text(f"<html>{TAG}{htmlmod.escape(payload)}</script></html>", encoding="utf-8")
        jp = tmp_path / "codemap.json"
        jp.write_text(json.dumps(_make_json({"total_modules": 1})), encoding="utf-8")
        r = validate_sync(hp, jp)
        assert r["sync"] is False
        assert "not an object" in r["reason"]

    def test_missing_display_keys_raises_keyerror(self, tmp_path):
        """Documented limitation (NOT filed - unreachable edge, cycle-200 rule).

        The success path (line 97) indexes json_summary['total_modules'/'total_errors'/'total_warnings']
        directly. A summary missing those keys raises KeyError instead of returning a dict.
        This is UNREACHABLE from the documented entry point: the generator
        (docs_generator.py:437/444/445) always writes all three keys, and the CLI
        main() only feeds generator-produced files. Pin the actual behavior so a
        future change to a graceful return is caught.
        """
        hp, jp = _write(tmp_path, _make_html({}), _make_json({}))
        with pytest.raises(KeyError):
            validate_sync(hp, jp)

    def test_minimal_required_keys_sync(self, tmp_path):
        """A summary with only the three display keys present -> sync True (reachable shape)."""
        s = {"total_modules": 1, "total_errors": 0, "total_warnings": 0}
        hp, jp = _write(tmp_path, _make_html(s), _make_json(s))
        r = validate_sync(hp, jp)
        assert r["sync"] is True
        assert r["summary"] == s


class TestValidateSyncIdempotence:
    def test_repeated_calls_stable(self, tmp_path):
        s = {"total_modules": 7, "total_lines": 200, "total_errors": 1, "total_warnings": 3}
        hp, jp = _write(tmp_path, _make_html(s), _make_json(s))
        r1 = validate_sync(hp, jp)
        r2 = validate_sync(hp, jp)
        assert r1 == r2
        assert r1["sync"] is True


# ---------------------------------------------------------------------------
# ARCH-93 adversarial: the one-sided (JSON -> HTML) contract, reverse half
# ---------------------------------------------------------------------------

class TestValidateSyncOneSidedReverse:
    """ARCH-93: the comparison is one-sided (JSON -> HTML).

    The corrected docstring states that a key present ONLY in the HTML-embedded
    summary is NOT compared and does not affect the result. The existing deep
    tests pin the JSON -> HTML half (a JSON key missing from HTML is a
    mismatch); this class pins the reverse half the docstring now documents:
    an HTML-only key is ignored, so the result stays sync True and the returned
    summary is the JSON summary (the HTML-only key is not surfaced).
    """

    def test_html_only_key_ignored_still_sync(self, tmp_path):
        """A key present only in the HTML-embedded summary is ignored."""
        s_json = {"total_modules": 1, "total_errors": 0, "total_warnings": 0}
        s_html = {"total_modules": 1, "total_errors": 0, "total_warnings": 0, "note": "extra"}
        hp, jp = _write(tmp_path, _make_html(s_html), _make_json(s_json))
        r = validate_sync(hp, jp)
        assert r["sync"] is True
        # The returned summary is the JSON summary; the HTML-only key is not surfaced.
        assert r["summary"] == s_json
        assert "note" not in r["summary"]

    def test_html_only_key_with_different_value_ignored(self, tmp_path):
        """Even if the HTML-only key carried a value, it is never visited."""
        s_json = {"total_modules": 5, "total_lines": 100, "total_errors": 0, "total_warnings": 2}
        s_html = dict(s_json)
        s_html["stale_field"] = 999
        hp, jp = _write(tmp_path, _make_html(s_html), _make_json(s_json))
        r = validate_sync(hp, jp)
        assert r["sync"] is True
        assert r["summary"] == s_json

    def test_html_only_unicode_key_ignored(self, tmp_path):
        """A unicode HTML-only key is likewise ignored (no crash, no surface)."""
        s_json = {"total_modules": 2, "total_errors": 0, "total_warnings": 0}
        s_html = dict(s_json)
        s_html["спасіба"] = "дзенница"
        hp, jp = _write(tmp_path, _make_html(s_html), _make_json(s_json))
        r = validate_sync(hp, jp)
        assert r["sync"] is True
        assert r["summary"] == s_json
