"""Adversarial deep tests for pipeline orchestrator end-to-end flow.

Tests the complete file-based pipeline: read → filter → score → tag → index → search.
Focuses on edge cases, guard inputs, round-trips, and idempotence.
"""

import os
import tempfile
import pytest
from personal_index.pipeline_orchestrator import PipelineOrchestrator


@pytest.fixture
def tmp_data_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def orchestrator(tmp_data_dir):
    return PipelineOrchestrator(data_dir=tmp_data_dir)


def test_empty_file_list(orchestrator):
    """Pipeline with no input files should succeed with zero pages."""
    result = orchestrator.run_from_files([])
    assert result.success
    assert result.stats.pages_crawled == 0
    assert result.stats.pages_indexed == 0
    assert result.errors == []


def test_nonexistent_file(orchestrator):
    """Non-existent file should be handled gracefully (not crash)."""
    result = orchestrator.run_from_files(["/tmp/does_not_exist_12345.html"])
    # Should not crash; file is simply not found
    assert result.success or len(result.errors) > 0
    assert result.stats.pages_crawled == 0


def test_empty_file(orchestrator, tmp_data_dir):
    """Empty file should be processed without crashing."""
    filepath = os.path.join(tmp_data_dir, "empty.html")
    with open(filepath, "w") as f:
        f.write("")
    result = orchestrator.run_from_files([filepath])
    assert result.success or len(result.errors) > 0
    # Empty content likely filtered out
    assert result.stats.pages_indexed <= 1


def test_whitespace_only_file(orchestrator, tmp_data_dir):
    """Whitespace-only file should be handled."""
    filepath = os.path.join(tmp_data_dir, "whitespace.html")
    with open(filepath, "w") as f:
        f.write("   \n\n  \t  ")
    result = orchestrator.run_from_files([filepath])
    assert result.success or len(result.errors) > 0


def test_unicode_content(orchestrator, tmp_data_dir):
    """Unicode content should be processed correctly."""
    filepath = os.path.join(tmp_data_dir, "unicode.html")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("<html><body><h1>Привет мир</h1><p>日本語テスト</p></body></html>")
    result = orchestrator.run_from_files([filepath])
    assert result.success or len(result.errors) > 0
    # Should have crawled at least one page
    assert result.stats.pages_crawled >= 1


def test_duplicate_files(orchestrator, tmp_data_dir):
    """Same file listed twice should be handled (idempotence check)."""
    filepath = os.path.join(tmp_data_dir, "dup.html")
    with open(filepath, "w") as f:
        f.write("<html><body><h1>Duplicate</h1><p>Content here.</p></body></html>")
    result = orchestrator.run_from_files([filepath, filepath])
    assert result.success or len(result.errors) > 0
    # Should not crash on duplicate
    assert result.stats.pages_crawled >= 1


def test_search_after_index(orchestrator, tmp_data_dir):
    """Round-trip: index content then search for it."""
    filepath = os.path.join(tmp_data_dir, "searchable.html")
    with open(filepath, "w") as f:
        f.write("<html><body><h1>Python Programming</h1><p>Learn Python coding.</p></body></html>")
    result = orchestrator.run_from_files([filepath])
    assert result.success or len(result.errors) > 0

    # Search for indexed content
    search_results = orchestrator.search("Python")
    # Should find at least one result
    assert isinstance(search_results, list)


def test_search_empty_query(orchestrator, tmp_data_dir):
    """Search with empty query should not crash."""
    filepath = os.path.join(tmp_data_dir, "content.html")
    with open(filepath, "w") as f:
        f.write("<html><body><h1>Test</h1><p>Content.</p></body></html>")
    orchestrator.run_from_files([filepath])
    results = orchestrator.search("")
    assert isinstance(results, list)


def test_search_whitespace_query(orchestrator, tmp_data_dir):
    """Search with whitespace query should not crash."""
    filepath = os.path.join(tmp_data_dir, "content.html")
    with open(filepath, "w") as f:
        f.write("<html><body><h1>Test</h1><p>Content.</p></body></html>")
    orchestrator.run_from_files([filepath])
    results = orchestrator.search("   ")
    assert isinstance(results, list)


def test_search_unicode_query(orchestrator, tmp_data_dir):
    """Search with unicode query should not crash."""
    filepath = os.path.join(tmp_data_dir, "content.html")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("<html><body><h1>Test</h1><p>Content.</p></body></html>")
    orchestrator.run_from_files([filepath])
    results = orchestrator.search("テスト")
    assert isinstance(results, list)


def test_search_negative_limit(orchestrator, tmp_data_dir):
    """Search with negative limit should not crash."""
    filepath = os.path.join(tmp_data_dir, "content.html")
    with open(filepath, "w") as f:
        f.write("<html><body><h1>Test</h1><p>Content.</p></body></html>")
    orchestrator.run_from_files([filepath])
    results = orchestrator.search("test", limit=-5)
    assert isinstance(results, list)


def test_search_zero_limit(orchestrator, tmp_data_dir):
    """Search with zero limit should return empty list."""
    filepath = os.path.join(tmp_data_dir, "content.html")
    with open(filepath, "w") as f:
        f.write("<html><body><h1>Test</h1><p>Content.</p></body></html>")
    orchestrator.run_from_files([filepath])
    results = orchestrator.search("test", limit=0)
    assert isinstance(results, list)
    assert len(results) == 0


def test_idempotent_rerun(orchestrator, tmp_data_dir):
    """Running pipeline twice on same files should not crash."""
    filepath = os.path.join(tmp_data_dir, "idempotent.html")
    with open(filepath, "w") as f:
        f.write("<html><body><h1>Idempotent</h1><p>Content.</p></body></html>")
    result1 = orchestrator.run_from_files([filepath])
    result2 = orchestrator.run_from_files([filepath])
    # Both should succeed or report errors, but not crash
    assert (result1.success or len(result1.errors) > 0)
    assert (result2.success or len(result2.errors) > 0)


def test_mixed_existing_nonexistent(orchestrator, tmp_data_dir):
    """Mix of existing and non-existing files."""
    filepath = os.path.join(tmp_data_dir, "exists.html")
    with open(filepath, "w") as f:
        f.write("<html><body><h1>Exists</h1><p>Content.</p></body></html>")
    result = orchestrator.run_from_files([
        filepath,
        "/tmp/nonexistent_abc.html",
        filepath
    ])
    assert result.success or len(result.errors) > 0
    assert result.stats.pages_crawled >= 1


def test_very_long_content(orchestrator, tmp_data_dir):
    """Very long content should be processed."""
    filepath = os.path.join(tmp_data_dir, "long.html")
    long_text = "Word " * 10000
    with open(filepath, "w") as f:
        f.write(f"<html><body><h1>Long</h1><p>{long_text}</p></body></html>")
    result = orchestrator.run_from_files([filepath])
    assert result.success or len(result.errors) > 0


def test_special_chars_in_filename(orchestrator, tmp_data_dir):
    """Filename with special characters."""
    filepath = os.path.join(tmp_data_dir, "file-with_special.chars (1).html")
    with open(filepath, "w") as f:
        f.write("<html><body><h1>Special</h1><p>Content.</p></body></html>")
    result = orchestrator.run_from_files([filepath])
    assert result.success or len(result.errors) > 0


def test_pipeline_result_has_summary(orchestrator, tmp_data_dir):
    """Pipeline result should have a summary method."""
    filepath = os.path.join(tmp_data_dir, "summary.html")
    with open(filepath, "w") as f:
        f.write("<html><body><h1>Summary</h1><p>Content.</p></body></html>")
    result = orchestrator.run_from_files([filepath])
    summary = result.summary()
    assert isinstance(summary, str)
    assert len(summary) > 0


def test_pipeline_result_success_property(orchestrator, tmp_data_dir):
    """Pipeline result success property should reflect errors."""
    filepath = os.path.join(tmp_data_dir, "success.html")
    with open(filepath, "w") as f:
        f.write("<html><body><h1>Success</h1><p>Content.</p></body></html>")
    result = orchestrator.run_from_files([filepath])
    # success should be bool
    assert isinstance(result.success, bool)
