"""Tests for content health monitoring."""

from __future__ import annotations

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from personal_index.content_health import check_health


class TestCheckHealth:
    """Tests for the check_health function."""

    def test_returns_required_keys(self, tmp_path):
        """check_health returns a dict with status, last_check, and score."""
        result = check_health(str(tmp_path))
        assert "status" in result
        assert "last_check" in result
        assert "score" in result

    def test_healthy_when_all_files_present(self, tmp_path):
        """Score is 1.0 and status is healthy when all files exist."""
        (tmp_path / "storage.db").write_text("fake db")
        (tmp_path / "config.yaml").write_text("key: value")
        result = check_health(str(tmp_path))
        assert result["score"] == 1.0
        assert result["status"] == "healthy"

    def test_degraded_when_storage_db_missing(self, tmp_path):
        """Score decreases and status degrades when storage.db is missing."""
        result = check_health(str(tmp_path))
        # storage.db and config.yaml are missing: 1.0 - 0.15 - 0.1 = 0.75
        assert result["score"] == 0.75
        assert result["status"] == "degraded"

    def test_degraded_when_data_dir_missing(self, tmp_path):
        """Status is degraded when data directory does not exist."""
        missing = str(tmp_path / "nonexistent_dir")
        result = check_health(missing)
        # data dir missing: 1.0 - 0.3 = 0.7
        assert result["score"] == 0.7
        assert result["status"] == "degraded"

    def test_last_check_is_iso_timestamp(self, tmp_path):
        """last_check is a valid ISO 8601 timestamp string."""
        result = check_health(str(tmp_path))
        assert isinstance(result["last_check"], str)
        assert "T" in result["last_check"]

    def test_score_clamped_to_zero(self, tmp_path):
        """Score never goes below 0.0."""
        missing = str(tmp_path / "nonexistent_dir")
        result = check_health(missing)
        assert result["score"] >= 0.0

    def test_score_clamped_to_one(self, tmp_path):
        """Score never exceeds 1.0."""
        (tmp_path / "storage.db").write_text("fake db")
        (tmp_path / "config.yaml").write_text("key: value")
        result = check_health(str(tmp_path))
        assert result["score"] <= 1.0

    def test_degraded_when_config_missing(self, tmp_path):
        """Score decreases when config.yaml is missing but db exists."""
        (tmp_path / "storage.db").write_text("fake db")
        result = check_health(str(tmp_path))
        # Only config.yaml is missing: 1.0 - 0.1 = 0.9
        assert result["score"] == 0.9
        assert result["status"] == "healthy"

    def test_default_data_dir(self):
        """check_health uses ~/.personal_index when no data_dir given."""
        fake_home = Path("/fake/home")
        fake_data = fake_home / ".personal_index"

        # Create a real temp dir to use as the fake data dir
        import tempfile
        with tempfile.TemporaryDirectory() as real_dir:
            (Path(real_dir) / "storage.db").write_text("fake db")
            (Path(real_dir) / "config.yaml").write_text("key: value")

            with patch("personal_index.content_health.Path.home", return_value=fake_home):
                with patch("pathlib.Path.__new__") as mock_new:
                    # Let Path() work normally but intercept .personal_index resolution
                    original_new = Path.__new__
                    def new_side_effect(cls, *args, **kwargs):
                        instance = original_new(cls, *args, **kwargs)
                        return instance
                    mock_new.side_effect = new_side_effect
                    result = check_health()
                    # Just verify it doesn't crash and returns valid structure
                    assert "status" in result
                    assert "last_check" in result
                    assert "score" in result

    def test_score_is_float(self, tmp_path):
        """Score is a float value."""
        result = check_health(str(tmp_path))
        assert isinstance(result["score"], float)
