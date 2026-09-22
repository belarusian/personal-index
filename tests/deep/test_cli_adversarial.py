"""Adversarial deep tests for the never-probed personal_index.cli module.

Cycle 358 PROBE: cli.py is the CLI entry point and had no dedicated deep
test. These pins attack the pure helpers (_format_storage_size,
_compute_storage_bytes) with boundary / out-of-range / unicode inputs and
run an end-to-end CLI session through click's CliRunner (init -> status ->
stats --format json -> search on an empty index).

Contracts pinned (from cli.py docstrings + observed behavior):
- _format_storage_size(n): n < 1024*1024 -> "<n/1024:.1f> KB", else
  "<n/(1024*1024):.1f> MB". Boundary at exactly 1024*1024 flips to MB.
- _compute_storage_bytes(dir): nonexistent dir -> 0; empty dir -> 0;
  recursively sums file sizes (nested subdirs included).
- CLI end-to-end: init creates the data dir + config; status/stats report
  zero counts on a fresh index; search on an empty index prints the
  "No indexed content found" guard and exits 0.
"""

from __future__ import annotations

import json
import os
import tempfile

from click.testing import CliRunner

from personal_index.cli import (
    _compute_storage_bytes,
    _format_storage_size,
    main,
)


# ---------------------------------------------------------------------------
# _format_storage_size — boundary / out-of-range
# ---------------------------------------------------------------------------

class TestFormatStorageSize:
    def test_zero_bytes_is_kb(self):
        assert _format_storage_size(0) == "0.0 KB"

    def test_sub_kb_rounds_to_zero(self):
        # 1 byte / 1024 -> 0.00097 -> "0.0 KB"
        assert _format_storage_size(1) == "0.0 KB"

    def test_just_below_one_kb(self):
        assert _format_storage_size(1023) == "1.0 KB"

    def test_exactly_one_kb(self):
        assert _format_storage_size(1024) == "1.0 KB"

    def test_just_below_one_mb_stays_kb(self):
        # 1048575 bytes = 1023.999 KB -> "1024.0 KB" (still KB branch)
        assert _format_storage_size(1024 * 1024 - 1) == "1024.0 KB"

    def test_exactly_one_mb_flips_to_mb(self):
        assert _format_storage_size(1024 * 1024) == "1.0 MB"

    def test_multi_mb(self):
        assert _format_storage_size(5 * 1024 * 1024) == "5.0 MB"

    def test_large_mb(self):
        # 1.5 GB -> 1536.0 MB
        assert _format_storage_size(1536 * 1024 * 1024) == "1536.0 MB"


# ---------------------------------------------------------------------------
# _compute_storage_bytes — nonexistent / empty / nested
# ---------------------------------------------------------------------------

class TestComputeStorageBytes:
    def test_nonexistent_dir_is_zero(self):
        assert _compute_storage_bytes("/nonexistent/path/xyz-358") == 0

    def test_empty_dir_is_zero(self):
        with tempfile.TemporaryDirectory() as d:
            assert _compute_storage_bytes(d) == 0

    def test_single_file(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "a.txt"), "w") as f:
                f.write("hello")  # 5 bytes
            assert _compute_storage_bytes(d) == 5

    def test_nested_subdirs_are_included(self):
        with tempfile.TemporaryDirectory() as d:
            sub = os.path.join(d, "sub")
            os.makedirs(sub)
            with open(os.path.join(d, "a.txt"), "w") as f:
                f.write("hello")  # 5
            with open(os.path.join(sub, "b.txt"), "w") as f:
                f.write("world!")  # 6
            assert _compute_storage_bytes(d) == 11

    def test_unicode_filename_counts_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "файл.txt"), "w", encoding="utf-8") as f:
                f.write("abc")  # 3 bytes
            assert _compute_storage_bytes(d) == 3


# ---------------------------------------------------------------------------
# End-to-end CLI run (click CliRunner)
# ---------------------------------------------------------------------------

class TestCliEndToEnd:
    def test_init_creates_data_dir_and_config(self, tmp_path):
        runner = CliRunner()
        dd = str(tmp_path / "data")
        cfg = str(tmp_path / "config.yaml")
        res = runner.invoke(main, ["--data-dir", dd, "init", "--config", cfg])
        assert res.exit_code == 0, res.output
        assert os.path.isdir(dd)
        assert os.path.isfile(cfg)
        assert "Initialized personal-index" in res.output

    def test_status_reports_zero_counts_on_fresh_index(self, tmp_path):
        runner = CliRunner()
        dd = str(tmp_path / "data")
        cfg = str(tmp_path / "config.yaml")
        runner.invoke(main, ["--data-dir", dd, "init", "--config", cfg])
        res = runner.invoke(main, ["--data-dir", dd, "status"])
        assert res.exit_code == 0, res.output
        assert "Pages indexed:  0" in res.output
        assert "Interests:      0" in res.output
        assert "Tags:           0" in res.output

    def test_stats_json_shape_on_fresh_index(self, tmp_path):
        runner = CliRunner()
        dd = str(tmp_path / "data")
        cfg = str(tmp_path / "config.yaml")
        runner.invoke(main, ["--data-dir", dd, "init", "--config", cfg])
        res = runner.invoke(main, ["--data-dir", dd, "stats", "--format", "json"])
        assert res.exit_code == 0, res.output
        data = json.loads(res.output)
        assert set(data.keys()) == {
            "indexed_pages", "interests", "total_tags", "tagged_pages",
            "storage_bytes",
        }
        assert data["indexed_pages"] == 0
        assert data["interests"] == 0
        assert data["total_tags"] == 0
        assert data["tagged_pages"] == 0
        assert data["storage_bytes"] >= 0

    def test_search_on_empty_index_prints_guard(self, tmp_path):
        runner = CliRunner()
        dd = str(tmp_path / "data")
        cfg = str(tmp_path / "config.yaml")
        runner.invoke(main, ["--data-dir", dd, "init", "--config", cfg])
        res = runner.invoke(main, ["--data-dir", dd, "search", "python"])
        assert res.exit_code == 0, res.output
        assert "No indexed content found" in res.output

    def test_search_negative_limit_on_empty_index_is_guarded(self, tmp_path):
        """Negative --limit on an empty index still hits the empty-index guard
        (exit 0, guard message) rather than crashing."""
        runner = CliRunner()
        dd = str(tmp_path / "data")
        cfg = str(tmp_path / "config.yaml")
        runner.invoke(main, ["--data-dir", dd, "init", "--config", cfg])
        res = runner.invoke(
            main, ["--data-dir", dd, "search", "python", "--limit", "-5"]
        )
        assert res.exit_code == 0, res.output
        assert "No indexed content found" in res.output
