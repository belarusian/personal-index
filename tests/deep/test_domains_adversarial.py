"""Cycle 170 PROBE: personal_index/domains.py (never-probed subsystem).

Adversarial deep tests for DomainRule / DomainManager:
  - DomainRule.to_dict / from_dict round-trip, missing-key defaults.
  - DomainManager._load: valid dict, corrupt JSON, non-dict top-level
    (graceful degradation), and structurally-malformed rule values.
  - is_allowed / is_blocked exact-match semantics, whitelist flag,
    max_pages boundary, page-count accounting.
  - remove / list_rules / get_max_depth / reset_counts.
  - one end-to-end run through the installed CLI (status).

Documented contract (docstrings) attacked:
  - to_dict/from_dict round-trip HOLDS for a well-formed rule.
  - _load degrades gracefully on corrupt JSON (json.JSONDecodeError caught)
    and on a non-dict top-level (isinstance guard) -> both HOLD.

DEFECTS FILED (pinned xfail-strict, flip to hard passes on fix):
  QA-11: _load crashes (TypeError) on a structurally-malformed rules file
    whose top-level is a dict but whose rule VALUE is not a mapping (or has
    an unexpected key). The except clause only catches
    (json.JSONDecodeError, KeyError), so the TypeError propagates and the
    whole manager fails to construct instead of degrading gracefully --
    contradicting the graceful-degradation intent the try/except establishes.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from personal_index.domains import DomainManager, DomainRule


# ---------------------------------------------------------------------------
# DomainRule serialization
# ---------------------------------------------------------------------------
class TestDomainRuleSerialization:
    def test_round_trip_well_formed(self):
        r = DomainRule(
            domain="example.com",
            allowed=False,
            max_pages=42,
            max_depth=7,
            reason="spam",
        )
        assert DomainRule.from_dict(r.to_dict()) == r

    def test_to_dict_has_exactly_five_keys(self):
        r = DomainRule(domain="x.com")
        assert set(r.to_dict().keys()) == {
            "domain",
            "allowed",
            "max_pages",
            "max_depth",
            "reason",
        }

    def test_from_dict_missing_keys_use_defaults(self):
        r = DomainRule.from_dict({"domain": "x.com"})
        assert r.domain == "x.com"
        assert r.allowed is True
        assert r.max_pages == 100
        assert r.max_depth == 3
        assert r.reason == ""

    def test_round_trip_idempotent(self):
        r = DomainRule(domain="a.com", allowed=True, max_pages=5, max_depth=2)
        once = DomainRule.from_dict(r.to_dict())
        twice = DomainRule.from_dict(once.to_dict())
        assert once == twice == r


# ---------------------------------------------------------------------------
# DomainManager._load graceful degradation
# ---------------------------------------------------------------------------
class TestLoadGracefulDegradation:
    def test_load_valid_dict(self, tmp_path):
        rf = tmp_path / "rules.json"
        rf.write_text(
            json.dumps({"ok.com": {"domain": "ok.com", "allowed": True}})
        )
        m = DomainManager(rules_file=str(rf))
        assert m.is_allowed("ok.com") is True

    def test_load_corrupt_json_degrades_to_empty(self, tmp_path):
        rf = tmp_path / "rules.json"
        rf.write_text("{not valid json")
        m = DomainManager(rules_file=str(rf))
        assert m.list_rules() == []

    def test_load_non_dict_toplevel_degrades_to_empty(self, tmp_path):
        rf = tmp_path / "rules.json"
        rf.write_text(json.dumps(["a", "b"]))
        m = DomainManager(rules_file=str(rf))
        assert m.list_rules() == []

    def test_load_missing_file_is_empty(self, tmp_path):
        m = DomainManager(rules_file=str(tmp_path / "nope.json"))
        assert m.list_rules() == []

    @pytest.mark.xfail(
        strict=True,
        reason="QA-11: _load crashes (TypeError) on a rule value that is not a mapping",
    )
    def test_load_non_mapping_value_degrades(self, tmp_path):
        rf = tmp_path / "rules.json"
        rf.write_text(json.dumps({"example.com": "notadict"}))
        m = DomainManager(rules_file=str(rf))
        # Contract implied by the try/except: malformed file degrades to empty.
        assert m.list_rules() == []

    @pytest.mark.xfail(
        strict=True,
        reason="QA-11: _load crashes (TypeError) on a rule dict with an unexpected key",
    )
    def test_load_extra_key_value_degrades(self, tmp_path):
        rf = tmp_path / "rules.json"
        rf.write_text(
            json.dumps(
                {
                    "example.com": {
                        "domain": "example.com",
                        "allowed": True,
                        "future_field": 1,
                    }
                }
            )
        )
        m = DomainManager(rules_file=str(rf))
        assert m.is_allowed("example.com") is True


# ---------------------------------------------------------------------------
# allow / block semantics
# ---------------------------------------------------------------------------
class TestAllowBlock:
    def test_add_allow_then_is_allowed(self):
        m = DomainManager()
        m.add_allow("ok.com")
        assert m.is_allowed("ok.com") is True
        assert m.is_blocked("ok.com") is False

    def test_add_block_then_is_blocked(self):
        m = DomainManager()
        m.add_block("spam.com", "bad")
        assert m.is_blocked("spam.com") is True
        assert m.is_allowed("spam.com") is False

    def test_block_does_not_set_whitelist(self):
        m = DomainManager()
        m.add_block("spam.com")
        # A block-only manager is NOT a whitelist: unlisted domains stay allowed.
        assert m.is_allowed("unlisted.com") is True

    def test_allow_sets_whitelist(self):
        m = DomainManager()
        m.add_allow("ok.com")
        # With a whitelist present, unlisted domains are disallowed.
        assert m.is_allowed("unlisted.com") is False

    def test_exact_match_case_sensitive(self):
        # Documented behavior: exact string match, no normalization.
        m = DomainManager()
        m.add_allow("example.com")
        assert m.is_allowed("example.com") is True
        assert m.is_allowed("EXAMPLE.com") is False

    def test_unlisted_no_rules_is_allowed(self):
        m = DomainManager()
        assert m.is_allowed("anything.com") is True


# ---------------------------------------------------------------------------
# page-count accounting
# ---------------------------------------------------------------------------
class TestPageCounts:
    def test_record_and_get(self):
        m = DomainManager()
        m.add_allow("c.com", max_pages=100)
        m.record_page("c.com")
        m.record_page("c.com")
        assert m.get_page_count("c.com") == 2

    def test_get_page_count_unknown_is_zero(self):
        m = DomainManager()
        assert m.get_page_count("ghost.com") == 0

    def test_max_pages_zero_disallows_immediately(self):
        m = DomainManager()
        m.add_allow("zero.com", max_pages=0)
        assert m.is_allowed("zero.com") is False

    def test_boundary_at_max_pages(self):
        m = DomainManager()
        m.add_allow("edge.com", max_pages=2)
        m.record_page("edge.com")
        assert m.is_allowed("edge.com") is True
        m.record_page("edge.com")
        # count == max_pages -> disallowed (>= comparison)
        assert m.is_allowed("edge.com") is False

    def test_reset_counts(self):
        m = DomainManager()
        m.add_allow("r.com", max_pages=1)
        m.record_page("r.com")
        assert m.is_allowed("r.com") is False
        m.reset_counts()
        assert m.get_page_count("r.com") == 0
        assert m.is_allowed("r.com") is True

    def test_page_counts_not_persisted_to_file(self, tmp_path):
        # Documented behavior (not a defect): _save persists rules only,
        # page counts are runtime state and reset on reload.
        rf = tmp_path / "rules.json"
        m = DomainManager(rules_file=str(rf))
        m.add_allow("p.com", max_pages=100)
        m.record_page("p.com")
        m2 = DomainManager(rules_file=str(rf))
        assert m2.get_page_count("p.com") == 0


# ---------------------------------------------------------------------------
# remove / list / max_depth
# ---------------------------------------------------------------------------
class TestRemoveListDepth:
    def test_remove_existing(self):
        m = DomainManager()
        m.add_allow("x.com")
        assert m.remove("x.com") is True
        assert m.is_allowed("x.com") is False

    def test_remove_missing(self):
        m = DomainManager()
        assert m.remove("ghost.com") is False

    def test_list_rules(self):
        m = DomainManager()
        m.add_allow("a.com")
        m.add_block("b.com")
        rules = m.list_rules()
        assert {r.domain for r in rules} == {"a.com", "b.com"}

    def test_get_max_depth_rule(self):
        m = DomainManager()
        m.add_allow("d.com", max_depth=9)
        assert m.get_max_depth("d.com") == 9

    def test_get_max_depth_default(self):
        m = DomainManager()
        assert m.get_max_depth("ghost.com") == 3


# ---------------------------------------------------------------------------
# end-to-end CLI
# ---------------------------------------------------------------------------
class TestCliEndToEnd:
    def test_status_runs(self, tmp_path):
        data_dir = str(tmp_path / "data")
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "personal_index",
                "--data-dir",
                data_dir,
                "status",
            ],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        assert "Personal Index Status" in proc.stdout
