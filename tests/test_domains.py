"""Tests for the domain management module."""

import json

from personal_index.domains import DomainManager, DomainRule


class TestDomainRule:
    def test_create_rule(self):
        rule = DomainRule(domain="example.com", allowed=True, max_pages=50)
        assert rule.domain == "example.com"
        assert rule.allowed is True
        assert rule.max_pages == 50

    def test_to_dict_and_from_dict(self):
        rule = DomainRule(domain="example.com", allowed=False, reason="spam")
        data = rule.to_dict()
        restored = DomainRule.from_dict(data)
        assert restored.domain == "example.com"
        assert restored.allowed is False
        assert restored.reason == "spam"


class TestDomainManager:
    def test_default_allows_all(self, tmp_path):
        dm = DomainManager(rules_file=str(tmp_path / "domains.json"))
        assert dm.is_allowed("example.com") is True

    def test_add_allow(self, tmp_path):
        dm = DomainManager(rules_file=str(tmp_path / "domains.json"))
        dm.add_allow("example.com", max_pages=50)
        assert dm.is_allowed("example.com") is True

    def test_add_block(self, tmp_path):
        dm = DomainManager(rules_file=str(tmp_path / "domains.json"))
        dm.add_block("spam.com", reason="spam site")
        assert dm.is_allowed("spam.com") is False
        assert dm.is_blocked("spam.com") is True

    def test_blocklist_blocks(self, tmp_path):
        dm = DomainManager(rules_file=str(tmp_path / "domains.json"))
        dm.add_block("spam.com")
        assert dm.is_allowed("spam.com") is False

    def test_whitelist_blocks_others(self, tmp_path):
        dm = DomainManager(rules_file=str(tmp_path / "domains.json"))
        dm.add_allow("allowed.com")
        assert dm.is_allowed("allowed.com") is True
        assert dm.is_allowed("not-allowed.com") is False

    def test_max_pages_limit(self, tmp_path):
        dm = DomainManager(rules_file=str(tmp_path / "domains.json"))
        dm.add_allow("example.com", max_pages=2)
        dm.record_page("example.com")
        dm.record_page("example.com")
        assert dm.is_allowed("example.com") is False

    def test_page_count(self, tmp_path):
        dm = DomainManager(rules_file=str(tmp_path / "domains.json"))
        dm.record_page("example.com")
        dm.record_page("example.com")
        assert dm.get_page_count("example.com") == 2

    def test_reset_counts(self, tmp_path):
        dm = DomainManager(rules_file=str(tmp_path / "domains.json"))
        dm.record_page("example.com")
        dm.reset_counts()
        assert dm.get_page_count("example.com") == 0

    def test_remove_rule(self, tmp_path):
        dm = DomainManager(rules_file=str(tmp_path / "domains.json"))
        dm.add_block("spam.com")
        assert dm.remove("spam.com") is True
        assert dm.is_blocked("spam.com") is False

    def test_remove_nonexistent(self, tmp_path):
        dm = DomainManager(rules_file=str(tmp_path / "domains.json"))
        assert dm.remove("nonexistent.com") is False

    def test_persistence(self, tmp_path):
        path = str(tmp_path / "domains.json")
        dm = DomainManager(rules_file=path)
        dm.add_block("spam.com", reason="spam")

        dm2 = DomainManager(rules_file=path)
        assert dm2.is_blocked("spam.com") is True

    def test_list_rules(self, tmp_path):
        dm = DomainManager(rules_file=str(tmp_path / "domains.json"))
        dm.add_allow("example.com")
        dm.add_block("spam.com")
        rules = dm.list_rules()
        assert len(rules) == 2

    def test_get_max_depth_default(self, tmp_path):
        dm = DomainManager(rules_file=str(tmp_path / "domains.json"))
        assert dm.get_max_depth("example.com") == 3

    def test_get_max_depth_custom(self, tmp_path):
        dm = DomainManager(rules_file=str(tmp_path / "domains.json"))
        dm.add_allow("example.com", max_depth=5)
        assert dm.get_max_depth("example.com") == 5

    def test_empty_rules(self, tmp_path):
        dm = DomainManager(rules_file=str(tmp_path / "domains.json"))
        assert dm.list_rules() == []


class TestDomainManagerLoadNonePath:
    """Tests for TICKET-28: _load() guards against None path."""

    def test_load_with_none_path_does_not_crash(self):
        """_load() should return early when rules_file is None."""
        mgr = DomainManager(rules_file=None)
        # Explicitly call _load() - should not raise TypeError
        mgr._load()
        assert mgr._rules == {}

    def test_load_with_none_path_after_init(self):
        """_load() called manually after init with None path should be safe."""
        mgr = DomainManager()
        mgr._load()
        assert mgr._rules == {}

    def test_save_with_none_path_does_not_crash(self):
        """_save() should return early when rules_file is None."""
        mgr = DomainManager(rules_file=None)
        mgr._save()
        # Should not raise any error


class TestDomainManagerNonDictGuard:
    """Tests for TICKET-276: _load() guards against non-dict JSON."""

    def _write(self, tmp_path, payload):
        path = str(tmp_path / "domains.json")
        with open(path, "w") as f:
            f.write(payload)
        return path

    def test_load_null_does_not_crash(self, tmp_path):
        path = self._write(tmp_path, "null")
        mgr = DomainManager(rules_file=path)
        assert mgr._rules == {}
        assert mgr.is_allowed("example.com") is True

    def test_load_number_does_not_crash(self, tmp_path):
        path = self._write(tmp_path, "42")
        mgr = DomainManager(rules_file=path)
        assert mgr._rules == {}

    def test_load_list_does_not_crash(self, tmp_path):
        path = self._write(tmp_path, json.dumps([1, 2, 3]))
        mgr = DomainManager(rules_file=path)
        assert mgr._rules == {}

    def test_valid_dict_still_works(self, tmp_path):
        path = str(tmp_path / "domains.json")
        dm = DomainManager(rules_file=path)
        dm.add_block("spam.com", reason="spam")
        dm2 = DomainManager(rules_file=path)
        assert dm2.is_blocked("spam.com") is True
        assert len(dm2.list_rules()) == 1

    def test_valid_after_invalid_not_suppressed(self, tmp_path):
        path = str(tmp_path / "domains.json")
        # write invalid (non-dict) first
        with open(path, "w") as f:
            f.write("null")
        bad = DomainManager(rules_file=path)
        assert bad._rules == {}
        # now write a valid dict and reload
        good = DomainManager(rules_file=path)
        good.add_block("spam.com", reason="spam")
        reloaded = DomainManager(rules_file=path)
        assert reloaded.is_blocked("spam.com") is True
