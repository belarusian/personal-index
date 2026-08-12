"""Tests for configuration loader."""

from pathlib import Path

import yaml

from personal_index.config.loader import (
    _parse_interest,
    _parse_match_mode,
    create_default_config,
    load_config,
    save_config,
)
from personal_index.config.models import (
    AppConfig,
    Interest,
    MatchMode,
)


class TestParseMatchMode:
    def test_any(self):
        assert _parse_match_mode("any") == MatchMode.ANY

    def test_all(self):
        assert _parse_match_mode("all") == MatchMode.ALL

    def test_regex(self):
        assert _parse_match_mode("regex") == MatchMode.REGEX

    def test_unknown_defaults_to_any(self):
        assert _parse_match_mode("unknown") == MatchMode.ANY

    def test_case_insensitive(self):
        assert _parse_match_mode("ANY") == MatchMode.ANY


class TestParseInterest:
    def test_minimal(self):
        interest = _parse_interest({"name": "test"})
        assert interest.name == "test"
        assert interest.keywords == []
        assert interest.match_mode == MatchMode.ANY

    def test_with_keywords(self):
        interest = _parse_interest({
            "name": "python",
            "keywords": ["python", "django"],
            "match_mode": "all",
            "priority": 8,
        })
        assert interest.keywords == ["python", "django"]
        assert interest.match_mode == MatchMode.ALL
        assert interest.priority == 8


class TestLoadConfig:
    def test_load_nonexistent_returns_defaults(self):
        config = load_config("/nonexistent/path.yaml")
        assert isinstance(config, AppConfig)
        assert config.interests == []

    def test_load_empty_file(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("")
        config = load_config(str(config_file))
        assert config.interests == []

    def test_load_with_interests(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
interests:
  - name: python
    keywords: [python, programming]
    priority: 8
  - name: rust
    keywords: [rust, systems]
    match_mode: all
    priority: 7
""")
        config = load_config(str(config_file))
        assert len(config.interests) == 2
        assert config.interests[0].name == "python"
        assert config.interests[0].priority == 8
        assert config.interests[1].match_mode == MatchMode.ALL

    def test_load_with_crawler_config(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
crawler:
  max_depth: 5
  politeness_delay: 2.0
  rate_limit: 20
""")
        config = load_config(str(config_file))
        assert config.crawler.max_depth == 5
        assert config.crawler.politeness_delay == 2.0
        assert config.crawler.rate_limit == 20


class TestSaveConfig:
    def test_save_and_reload(self, tmp_path):
        config = AppConfig(
            interests=[Interest(name="test", keywords=["a", "b"])],
        )
        config_file = tmp_path / "config.yaml"
        save_config(config, str(config_file))

        assert config_file.exists()
        loaded = load_config(str(config_file))
        assert len(loaded.interests) == 1
        assert loaded.interests[0].name == "test"

    def test_save_creates_parent_dirs(self, tmp_path):
        config = AppConfig()
        config_file = tmp_path / "sub" / "dir" / "config.yaml"
        save_config(config, str(config_file))
        assert config_file.exists()

    def test_save_yaml_format(self, tmp_path):
        config = AppConfig(interests=[Interest(name="test")])
        config_file = tmp_path / "config.yaml"
        save_config(config, str(config_file))

        with open(config_file) as f:
            data = yaml.safe_load(f)
        assert "interests" in data
        assert data["interests"][0]["name"] == "test"


class TestCreateDefaultConfig:
    def test_creates_file(self, tmp_path):
        config_file = tmp_path / "default.yaml"
        result = create_default_config(str(config_file))
        assert Path(result).exists()
        assert result == str(config_file)

    def test_default_config_loads(self, tmp_path):
        config_file = tmp_path / "default.yaml"
        create_default_config(str(config_file))
        config = load_config(str(config_file))
        assert isinstance(config, AppConfig)
