"""Pytest configuration and fixtures."""

import os
import shutil

import pytest


@pytest.fixture(autouse=True)
def cleanup_personal_index():
    """Clean up .personal_index directory before and after each test."""
    personal_index = ".personal_index"
    # Clean up before test
    if os.path.exists(personal_index):
        if os.path.islink(personal_index):
            os.unlink(personal_index)
        elif os.path.isdir(personal_index):
            shutil.rmtree(personal_index)
        else:
            os.remove(personal_index)

    yield

    # Clean up after test
    if os.path.exists(personal_index):
        if os.path.islink(personal_index):
            os.unlink(personal_index)
        elif os.path.isdir(personal_index):
            shutil.rmtree(personal_index)
        else:
            os.remove(personal_index)
