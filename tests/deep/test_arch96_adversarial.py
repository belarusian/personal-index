"""Adversarial deep tests for ARCH-96: score-threshold drop counter.

ARCH-96 (IMPLEMENTED #1563@190df07) added ``PipelineRunResult.pages_score_filtered_out``
and increments it exactly once per page that passes the content filter but scores
below ``config.min_score_threshold``. The contract (tickets/ARCH-96.md):

  * field defaults to 0 (existing construction unaffected);
  * incremented ONLY on the score-threshold drop (``score < min_score_threshold``);
  * NEVER incremented for filter drops, read errors, or index errors;
  * ``min_score_threshold=0.0`` (default) leaves the counter at 0;
  * ``summary()`` prints the new counter;
  * funnel reconciles: ``pages_filtered_in == pages_indexed + pages_score_filtered_out``
    (when no index errors).

These tests pin that contract under adversarial inputs (empty, missing, filter-drop,
index-error, boundary-equal, duplicate, unicode, whitespace) and run one end-to-end
CLI pass through the installed entry point.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from personal_index.config.pipeline_config import PipelineConfig
from personal_index.pipeline_e2e import PipelineE2E, PipelineRunResult

# A page that passes the content filter (>= min_content_length=10 chars, title >= 3)
# and matches the "python" keyword -> scores high enough to clear a 0.5 threshold.
MATCH_CONTENT = (
    "Python Python Python Python Python Python Python Python "
    "Python Python Python programming language for development."
)
# A page that passes the content filter but matches NO keyword -> scores below 0.5.
NOMATCH_CONTENT = (
    "This article is about cooking recipes and baking "
    "techniques for home chefs and professional bakers."
)


def _make_pipeline(tmp_path: Path, threshold: float) -> PipelineE2E:
    pipeline = PipelineE2E(
        data_dir=str(tmp_path / "data"),
        config=PipelineConfig(min_score_threshold=threshold),
    )
    pipeline.add_interest(name="python", keywords=["python"], priority=10)
    return pipeline


def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# Contract pins (the implementer's acceptance criteria, re-pinned adversarially)
# ---------------------------------------------------------------------------

def test_normal_case_counter_and_funnel(tmp_path: Path) -> None:
    """One match + one no-match at threshold 0.5 -> exactly one score drop."""
    pipeline = _make_pipeline(tmp_path, 0.5)
    good = _write(tmp_path, "good.txt", MATCH_CONTENT)
    bad = _write(tmp_path, "bad.txt", NOMATCH_CONTENT)

    result = pipeline.run_from_files([good, bad])

    assert result.pages_score_filtered_out == 1
    assert result.pages_filtered_in == 2
    assert result.pages_scored == 2
    assert result.pages_indexed == 1
    # Funnel reconciles (no index errors in this run).
    assert result.pages_filtered_in == (
        result.pages_indexed + result.pages_score_filtered_out
    )
    pipeline.close()


def test_guard_zero_threshold_leaves_counter_zero(tmp_path: Path) -> None:
    """Default threshold 0.0 -> no page scores below 0.0 -> counter stays 0."""
    pipeline = _make_pipeline(tmp_path, 0.0)
    good = _write(tmp_path, "good.txt", MATCH_CONTENT)
    bad = _write(tmp_path, "bad.txt", NOMATCH_CONTENT)

    result = pipeline.run_from_files([good, bad])

    assert result.pages_score_filtered_out == 0
    assert result.pages_indexed == 2
    pipeline.close()


def test_field_defaults_to_zero() -> None:
    """A fresh PipelineRunResult has pages_score_filtered_out == 0 (AC-1)."""
    assert PipelineRunResult().pages_score_filtered_out == 0


def test_summary_prints_new_counter(tmp_path: Path) -> None:
    """summary() surfaces the score-filtered-out counter (AC-3)."""
    pipeline = _make_pipeline(tmp_path, 0.5)
    good = _write(tmp_path, "good.txt", MATCH_CONTENT)
    bad = _write(tmp_path, "bad.txt", NOMATCH_CONTENT)

    result = pipeline.run_from_files([good, bad])
    summary = result.summary()

    assert "Score filtered out:" in summary
    assert "Score filtered out:1" in summary
    pipeline.close()


# ---------------------------------------------------------------------------
# Adversarial: the counter must NOT fire on non-score drops
# ---------------------------------------------------------------------------

def test_empty_file_list_all_counters_zero(tmp_path: Path) -> None:
    """run_from_files([]) -> every counter 0, success True, no errors."""
    pipeline = _make_pipeline(tmp_path, 0.5)
    result = pipeline.run_from_files([])

    assert result.pages_crawled == 0
    assert result.pages_filtered_in == 0
    assert result.pages_scored == 0
    assert result.pages_score_filtered_out == 0
    assert result.pages_indexed == 0
    assert result.success is True
    assert result.errors == []
    pipeline.close()


def test_missing_file_is_read_error_not_score_drop(tmp_path: Path) -> None:
    """A nonexistent path is a read error, never a score-threshold drop."""
    pipeline = _make_pipeline(tmp_path, 0.5)
    result = pipeline.run_from_files([str(tmp_path / "does_not_exist.txt")])

    assert result.pages_score_filtered_out == 0
    assert result.pages_scored == 0
    assert result.pages_indexed == 0
    assert result.success is False
    assert any("File not found" in e for e in result.errors)
    pipeline.close()


def test_filter_drop_is_not_score_drop(tmp_path: Path) -> None:
    """Short content is filtered out before scoring -> counter stays 0."""
    pipeline = _make_pipeline(tmp_path, 0.5)
    short = _write(tmp_path, "short.txt", "Too short")  # 9 chars < min 10

    result = pipeline.run_from_files([short])

    assert result.pages_filtered_out == 1
    assert result.pages_filtered_in == 0
    assert result.pages_scored == 0  # never reached the score stage
    assert result.pages_score_filtered_out == 0
    assert result.pages_indexed == 0
    pipeline.close()


def test_index_error_is_not_score_drop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A page that scores above threshold but fails to index is an index error,
    not a score drop. Pins the 'never incremented for index errors' contract."""
    pipeline = _make_pipeline(tmp_path, 0.5)
    good = _write(tmp_path, "good.txt", MATCH_CONTENT)

    def _boom(page) -> None:
        raise ValueError("index exploded")

    monkeypatch.setattr(pipeline, "_stage_index", _boom)

    result = pipeline.run_from_files([good])

    assert result.pages_scored == 1
    assert result.pages_score_filtered_out == 0  # NOT a score drop
    assert result.pages_indexed == 0
    assert result.success is False
    assert any("Index error" in e for e in result.errors)
    # Documented invariant: filtered_in == indexed + score_filtered_out + index_errors
    assert result.pages_filtered_in == (
        result.pages_indexed + result.pages_score_filtered_out + 1
    )
    pipeline.close()


# ---------------------------------------------------------------------------
# Adversarial: boundary and multiplicity
# ---------------------------------------------------------------------------

def test_boundary_score_equal_to_threshold_is_not_dropped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Contract uses strict ``score < threshold``: a score EQUAL to the threshold
    is NOT below it, so it is indexed, not counted as a score drop."""
    pipeline = _make_pipeline(tmp_path, 0.5)
    good = _write(tmp_path, "good.txt", MATCH_CONTENT)

    # Force the score to be exactly the threshold.
    monkeypatch.setattr(pipeline, "_stage_score", lambda page: 0.5)

    result = pipeline.run_from_files([good])

    assert result.pages_score_filtered_out == 0
    assert result.pages_indexed == 1
    pipeline.close()


def test_boundary_score_just_below_threshold_is_dropped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A score just below the threshold IS counted exactly once."""
    pipeline = _make_pipeline(tmp_path, 0.5)
    good = _write(tmp_path, "good.txt", MATCH_CONTENT)

    monkeypatch.setattr(pipeline, "_stage_score", lambda page: 0.4999)

    result = pipeline.run_from_files([good])

    assert result.pages_score_filtered_out == 1
    assert result.pages_indexed == 0
    pipeline.close()


def test_multiple_no_match_files_count_each(tmp_path: Path) -> None:
    """N no-match files at threshold 0.5 -> counter == N, funnel reconciles."""
    pipeline = _make_pipeline(tmp_path, 0.5)
    paths = [_write(tmp_path, f"bad_{i}.txt", NOMATCH_CONTENT) for i in range(4)]

    result = pipeline.run_from_files(paths)

    assert result.pages_score_filtered_out == 4
    assert result.pages_filtered_in == 4
    assert result.pages_indexed == 0
    assert result.pages_filtered_in == (
        result.pages_indexed + result.pages_score_filtered_out
    )
    pipeline.close()


def test_duplicate_file_does_not_corrupt_counter(tmp_path: Path) -> None:
    """The same file path processed twice: the counter counts processing events,
    stays 0 (both match), and the funnel still reconciles."""
    pipeline = _make_pipeline(tmp_path, 0.5)
    good = _write(tmp_path, "good.txt", MATCH_CONTENT)

    result = pipeline.run_from_files([good, good])

    assert result.pages_score_filtered_out == 0
    assert result.pages_filtered_in == 2
    assert result.pages_indexed == 2
    assert result.pages_filtered_in == (
        result.pages_indexed + result.pages_score_filtered_out
    )
    pipeline.close()


# ---------------------------------------------------------------------------
# Adversarial: unicode + whitespace content
# ---------------------------------------------------------------------------

def test_unicode_keyword_match_and_no_match(tmp_path: Path) -> None:
    """Unicode content: a match clears the threshold, a no-match is counted."""
    pipeline = _make_pipeline(tmp_path, 0.5)
    match = _write(
        tmp_path, "match.txt",
        "Python Python Python Python Python Python Python Python "
        "Python Python Python — café résumé naïve 日本語 development.",
    )
    nomatch = _write(
        tmp_path, "nomatch.txt",
        "Café recipes: baking techniques for home chefs — "
        "résumé of professional bakers 日本語.",
    )

    result = pipeline.run_from_files([match, nomatch])

    assert result.pages_score_filtered_out == 1
    assert result.pages_indexed == 1
    pipeline.close()


def test_whitespace_only_content_is_score_drop(tmp_path: Path) -> None:
    """Whitespace-only content that clears the length filter but matches no keyword
    scores below threshold -> counted exactly once."""
    pipeline = _make_pipeline(tmp_path, 0.5)
    ws = _write(tmp_path, "ws.txt", "   \n\t   \n   ")  # 11 chars, no keyword

    result = pipeline.run_from_files([ws])

    assert result.pages_filtered_in == 1
    assert result.pages_scored == 1
    assert result.pages_score_filtered_out == 1
    assert result.pages_indexed == 0
    pipeline.close()


# ---------------------------------------------------------------------------
# End-to-end CLI run through the installed entry point
# ---------------------------------------------------------------------------


def test_cli_end_to_end_import(tmp_path: Path) -> None:
    """One end-to-end CLI pass: init + import a real file through the installed
    ``personal-index`` entry point (click CliRunner)."""
    from click.testing import CliRunner

    from personal_index.cli import main

    runner = CliRunner(isolate_filesystem=False)
    data_dir = str(tmp_path / "cli_data")

    init_res = runner.invoke(main, ["init", "--data-dir", data_dir])
    assert init_res.exit_code == 0, init_res.output
    assert "Initialized personal-index" in init_res.output

    article = tmp_path / "article.txt"
    article.write_text(
        "Python is a versatile programming language used for web development, "
        "data science, and automation across many paradigms.",
        encoding="utf-8",
    )

    import_res = runner.invoke(
        main,
        ["import", str(article), "--data-dir", data_dir],
    )
    assert import_res.exit_code == 0, import_res.output
    assert "Import complete: 1 file(s) imported" in import_res.output

    # The import persisted an index file under the data dir.
    assert os.path.exists(os.path.join(data_dir, "search_index.json"))

