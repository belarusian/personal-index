"""Adversarial deep tests for personal_index.pipeline_orchestrator stats counters.

Cycle 150 - VALIDATOR VERIFY of ARCH-9 (single-source pages_tagged /
pages_indexed counters).

ARCH-9 contract (tickets/ARCH-9.md):
  - ``stats.pages_tagged`` and ``stats.pages_indexed`` are each written by
    EXACTLY ONE site: the stage runners ``_run_tag_stage`` /
    ``_run_index_stage`` via ``= len(out)`` (the last write wins). The
    per-page ``+= 1`` increments that used to live in ``_apply_tag`` /
    ``_apply_index`` are GONE.
  - The counters therefore equal the KEPT count (``len(out)``), NOT the
    attempted count. The old latent invariant ("all callbacks return True")
    must no longer be load-bearing: if a callback ever returns False (drops a
    page), the counter must still equal the kept count.

Tests:
  - counters equal kept (not attempted) when the filter drops pages
  - counters equal kept (not attempted) when _apply_tag itself returns False
    (the exact latent invariant ARCH-9 was about)
  - empty input -> counters 0
  - a second run does not accumulate on the first (fresh result per run)
  - one end-to-end CLI run through the installed entry point.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from personal_index.models import CrawledPage
from personal_index.pipeline_orchestrator import PipelineOrchestrator


# --- fixtures -----------------------------------------------------------------

@pytest.fixture
def orchestrator(tmp_path: Path) -> PipelineOrchestrator:
    return PipelineOrchestrator(data_dir=str(tmp_path / "data"))


def _page(url: str, content: str, title: str = "page") -> CrawledPage:
    return CrawledPage(url=url, title=title, content=content,
                       word_count=len(content.split()))


def _write_file(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# --- 1. counters equal KEPT, not attempted (filter drop path) -----------------

def test_counters_equal_kept_not_attempted(orchestrator, tmp_path):
    """3 pages pass the filter, 2 are dropped (short content). The tag/index
    counters must equal the KEPT count (3), not the attempted count (5)."""
    keep = "Python is a programming language used in data science and machine learning."
    drop = "tiny"  # < min_content_length (10) -> filtered out
    files = [
        _write_file(tmp_path, f"keep{i}.txt", keep) for i in range(3)
    ] + [
        _write_file(tmp_path, f"drop{i}.txt", drop) for i in range(2)
    ]
    result = orchestrator.run_from_files([str(f) for f in files])
    s = result.stats
    assert s.pages_crawled == 5
    assert s.pages_passed_filter == 3
    assert s.pages_filtered_out == 2
    # The exact latent invariant: counters track KEPT, not attempted.
    assert s.pages_tagged == 3, f"pages_tagged={s.pages_tagged} (expected kept=3, not attempted=5)"
    assert s.pages_indexed == 3, f"pages_indexed={s.pages_indexed} (expected kept=3, not attempted=5)"
    assert s.pages_tagged == s.pages_indexed == s.pages_passed_filter
    assert s.pages_tagged != 5


# --- 2. the EXACT latent invariant: _apply_tag returns False ------------------

def test_apply_tag_false_counter_still_kept(orchestrator, tmp_path):
    """Directly exercise the scenario ARCH-9 was about: a tag callback that
    returns False (drops a page). The counter must still equal the kept count,
    not the attempted count. If a per-page ``+= 1`` were re-introduced in
    _apply_tag, pages_tagged would count the dropped page and this fails."""
    keep = "Python is a programming language used in data science and machine learning."
    files = [
        _write_file(tmp_path, f"p{i}.txt", keep) for i in range(3)
    ]
    # Drop the middle page at the tag stage.
    orig = orchestrator._apply_tag

    def fake_apply_tag(page, result):
        if page.url.endswith("p1.txt"):
            return False
        return orig(page, result)

    orchestrator._apply_tag = fake_apply_tag
    try:
        result = orchestrator.run_from_files([str(f) for f in files])
    finally:
        orchestrator._apply_tag = orig
    s = result.stats
    assert s.pages_passed_filter == 3
    # 2 of 3 kept at the tag stage -> counter must be 2, not the attempted 3.
    assert s.pages_tagged == 2, f"pages_tagged={s.pages_tagged} (expected kept=2, not attempted=3)"
    assert s.pages_indexed == 2
    assert s.pages_tagged != 3


# --- 3. empty input -> counters 0 ---------------------------------------------

def test_empty_input_counters_zero(orchestrator):
    result = orchestrator.run_from_files([])
    s = result.stats
    assert s.pages_crawled == 0
    assert s.pages_extracted == 0
    assert s.pages_passed_filter == 0
    assert s.pages_filtered_out == 0
    assert s.pages_scored == 0
    assert s.pages_tagged == 0
    assert s.pages_indexed == 0
    assert s.tags_applied == 0
    assert result.pages == []


# --- 4. no accumulation across runs (fresh result per run) ---------------------

def test_second_run_does_not_accumulate(orchestrator, tmp_path):
    keep = "Python is a programming language used in data science and machine learning."
    f = _write_file(tmp_path, "only.txt", keep)
    r1 = orchestrator.run_from_files([str(f)])
    r2 = orchestrator.run_from_files([str(f)])
    # Each run is independent: a fresh PipelineResult, so counters reflect only
    # that run's pages (no cross-run accumulation on the stats object).
    assert r1.stats.pages_tagged == 1
    assert r2.stats.pages_tagged == 1
    assert r1.stats.pages_indexed == 1
    assert r2.stats.pages_indexed == 1
    assert r1 is not r2


# --- 5. end-to-end CLI run -----------------------------------------------------

def test_cli_pipeline_e2e(tmp_path):
    """One end-to-end run through the installed CLI entry point. The CLI
    ``pipeline`` command drives PipelineRunner (a separate class); this is a
    smoke check that the installed entry point runs the full pipeline and
    reports the tag/index counters without error."""
    f = tmp_path / "sample.txt"
    f.write_text(
        "Python is a programming language. "
        "Python is used in data science and machine learning. "
        "Python has great libraries for many tasks.",
        encoding="utf-8",
    )
    data_dir = tmp_path / "cli_data"
    result = subprocess.run(
        [
            sys.executable, "-m", "personal_index",
            "pipeline", "--import-file", str(f),
            "--data-dir", str(data_dir),
        ],
        capture_output=True, text=True,
        cwd=str(Path(__file__).resolve().parent.parent.parent),
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "Pipeline complete" in result.stdout
    assert "Tagged:" in result.stdout
    assert "Indexed:" in result.stdout
