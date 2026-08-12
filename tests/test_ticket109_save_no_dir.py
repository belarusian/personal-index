"""Test TICKET-109: Fix _save when rules_file has no directory component"""

import os

from personal_index.domains import DomainManager


def test_save_with_no_directory_component(tmp_path, monkeypatch):
    """Verify _save works when rules_file has no directory component."""
    monkeypatch.chdir(str(tmp_path))
    dm = DomainManager(rules_file="rules.json")
    dm.add_allow("example.com")
    assert os.path.exists("rules.json")
    assert dm.is_allowed("example.com")


def test_save_with_directory_component(tmp_path):
    """Verify _save works when rules_file has a directory component."""
    rules_path = str(tmp_path / "subdir" / "rules.json")
    dm = DomainManager(rules_file=rules_path)
    dm.add_allow("example.com")
    assert os.path.exists(rules_path)
    assert dm.is_allowed("example.com")


def test_save_with_empty_dirname():
    """Verify os.path.dirname returns empty string for bare filename."""
    assert os.path.dirname("rules.json") == ""
    # The or "." pattern should handle this
    dirname = os.path.dirname("rules.json") or "."
    assert dirname == "."
