"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture(autouse=True)
def cleanup_personal_index(tmp_path, monkeypatch):
    """Run each test in its own temp directory to avoid .personal_index permission errors."""
    monkeypatch.chdir(tmp_path)
    yield
