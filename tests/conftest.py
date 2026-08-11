"""Pytest configuration and fixtures."""

import os
import shutil
import tempfile

import pytest


@pytest.fixture(autouse=True)
def cleanup_personal_index():
    """Clean up .personal_index directory before and after each test."""
    # Save original state if exists
    personal_index = ".personal_index"
    backup = None
    if os.path.exists(personal_index):
        backup = tempfile.mkdtemp(prefix="personal_index_backup_")
        shutil.copytree(personal_index, os.path.join(backup, "personal_index"))
    
    # Clean up before test
    if os.path.exists(personal_index):
        shutil.rmtree(personal_index)
    
    yield
    
    # Restore after test
    if backup and os.path.exists(os.path.join(backup, "personal_index")):
        if os.path.exists(personal_index):
            shutil.rmtree(personal_index)
        shutil.move(os.path.join(backup, "personal_index"), personal_index)
        shutil.rmtree(backup)
