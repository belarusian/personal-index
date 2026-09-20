"""Pytest configuration and fixtures."""

import os
import shutil
import tempfile

import pytest


@pytest.fixture(autouse=True)
def cleanup_personal_index():
    """Clean up .personal_index directory before and after each test."""
    personal_index = ".personal_index"
    backup = None
    if os.path.exists(personal_index):
        backup = tempfile.mkdtemp(prefix="personal_index_backup_")
        if os.path.isdir(personal_index):
            shutil.copytree(personal_index, os.path.join(backup, "personal_index"))
        else:
            shutil.copy2(personal_index, os.path.join(backup, "personal_index"))

    # Clean up before test
    if os.path.exists(personal_index):
        if os.path.isdir(personal_index):
            shutil.rmtree(personal_index)
        else:
            os.remove(personal_index)

    yield

    # Restore after test
    if backup and os.path.exists(os.path.join(backup, "personal_index")):
        if os.path.exists(personal_index):
            if os.path.isdir(personal_index):
                shutil.rmtree(personal_index)
            else:
                os.remove(personal_index)
        backup_src = os.path.join(backup, "personal_index")
        if os.path.isdir(backup_src):
            shutil.move(backup_src, personal_index)
        else:
            shutil.move(backup_src, personal_index)
        shutil.rmtree(backup)
