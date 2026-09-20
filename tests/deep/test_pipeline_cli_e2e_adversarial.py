"""End-to-end CLI test for the pipeline command.

Runs the actual CLI with adversarial inputs to verify the complete
file-based pipeline works through the user-facing interface.
"""

import os
import tempfile
import subprocess
import pytest


def run_cli(*args, data_dir=None):
    """Run the personal-index CLI and return the result."""
    cmd = ["python3", "-m", "personal_index"]
    if data_dir:
        cmd += ["--data-dir", data_dir]
    cmd += list(args)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30)


@pytest.fixture
def tmp_data_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


def test_cli_pipeline_empty_import(tmp_data_dir):
    """CLI pipeline with no import files should report missing input."""
    result = run_cli("pipeline", data_dir=tmp_data_dir)
    # Exit code 1 with "No URLs or files specified" is expected
    assert result.returncode == 1
    assert "No URLs or files specified" in result.stdout or "No URLs or files specified" in result.stderr


def test_cli_pipeline_nonexistent_file(tmp_data_dir):
    """CLI pipeline with nonexistent import file should not crash."""
    result = run_cli("pipeline", "--import-file", "/tmp/does_not_exist_12345.html",
                     data_dir=tmp_data_dir)
    # Should not crash (returncode 0 or handled error)
    assert result.returncode in (0, 1)


def test_cli_pipeline_valid_file(tmp_data_dir):
    """CLI pipeline with a valid HTML file should succeed."""
    filepath = os.path.join(tmp_data_dir, "test.html")
    with open(filepath, "w") as f:
        f.write("<html><head><title>Test</title></head><body><h1>Test</h1><p>Content here for testing.</p></body></html>")
    result = run_cli("pipeline", "--import-file", filepath, data_dir=tmp_data_dir)
    assert result.returncode == 0


def test_cli_pipeline_unicode_file(tmp_data_dir):
    """CLI pipeline with unicode content should succeed."""
    filepath = os.path.join(tmp_data_dir, "unicode.html")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("<html><head><title>テスト</title></head><body><h1>テスト</h1><p>日本語のテストコンテンツです。</p></body></html>")
    result = run_cli("pipeline", "--import-file", filepath, data_dir=tmp_data_dir)
    assert result.returncode == 0


def test_cli_pipeline_empty_file(tmp_data_dir):
    """CLI pipeline with empty file should not crash."""
    filepath = os.path.join(tmp_data_dir, "empty.html")
    with open(filepath, "w") as f:
        f.write("")
    result = run_cli("pipeline", "--import-file", filepath, data_dir=tmp_data_dir)
    assert result.returncode == 0


def test_cli_search_after_pipeline(tmp_data_dir):
    """Search should work after running pipeline."""
    filepath = os.path.join(tmp_data_dir, "searchable.html")
    with open(filepath, "w") as f:
        f.write("<html><head><title>Python</title></head><body><h1>Python</h1><p>Learn Python programming.</p></body></html>")
    run_cli("pipeline", "--import-file", filepath, data_dir=tmp_data_dir)
    result = run_cli("search", "Python", data_dir=tmp_data_dir)
    assert result.returncode == 0
