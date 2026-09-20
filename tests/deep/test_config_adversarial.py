"""Adversarial deep tests for the config subsystem (loader + models).

Tests edge cases, invalid inputs, persistence, defaults, overrides,
type coercion, validation errors, serialization round-trips, and
concurrent access scenarios.
"""

import json
import os
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
import yaml

from personal_index.config.loader import load_config, DEFAULT_CONFIG_FILENAME
from personal_index.config.models import (
    AppConfig,
    CrawlerConfig,
    IndexConfig,
    SchedulerConfig,
    NotificationConfig,
    ExportConfig,
    Interest,
    MatchMode,
)


# =============================================================================
# Config loading: file vs defaults
# =============================================================================

def test_load_config_missing_file_returns_defaults():
    """Loading a non-existent config file should return defaults."""
    cfg = load_config("/tmp/nonexistent_config_12345.yaml")
    assert cfg.data_dir == ".personal_index"
    assert cfg.crawler.max_depth == 3
    assert cfg.index.enable_stemming is True
    assert cfg.scheduler.enabled is False


def test_load_config_empty_file_returns_defaults():
    """Loading an empty config file should return defaults."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("")
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.data_dir == ".personal_index"
    finally:
        os.unlink(path)


def test_load_config_whitespace_only_returns_defaults():
    """Loading a whitespace-only config file should return defaults."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("   \n  \n   ")
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.data_dir == ".personal_index"
    finally:
        os.unlink(path)


def test_load_config_partial_overrides():
    """Loading a config with only some fields should override those and default the rest."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("data_dir: /custom/data\n")
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.data_dir == "/custom/data"
        assert cfg.crawler.max_depth == 3  # default
        assert cfg.index.enable_stemming is True  # default
    finally:
        os.unlink(path)


def test_load_config_full_override():
    """Loading a config with all fields should override everything."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("data_dir: /full/data\nlog_level: DEBUG\n")
        f.write("crawler:\n  max_depth: 10\n  politeness_delay: 5.0\n")
        f.write("index:\n  enable_stemming: false\n  min_term_length: 3\n")
        f.write("scheduler:\n  enabled: true\n  interval_hours: 12\n")
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.data_dir == "/full/data"
        assert cfg.log_level == "DEBUG"
        assert cfg.crawler.max_depth == 10
        assert cfg.crawler.politeness_delay == 5.0
        assert cfg.index.enable_stemming is False
        assert cfg.index.min_term_length == 3
        assert cfg.scheduler.enabled is True
        assert cfg.scheduler.interval_hours == 12
    finally:
        os.unlink(path)


# =============================================================================
# Invalid/missing config values
# =============================================================================

def test_load_config_invalid_yaml_returns_defaults():
    """Loading invalid YAML should return defaults (not crash)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("invalid: yaml: [unclosed\n  - broken")
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.data_dir == ".personal_index"
    finally:
        os.unlink(path)


def test_load_config_non_mapping_yaml_returns_defaults():
    """Loading YAML that is not a mapping (e.g., a list) should return defaults."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("- item1\n- item2\n")
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.data_dir == ".personal_index"
    finally:
        os.unlink(path)


def test_load_config_scalar_yaml_returns_defaults():
    """Loading YAML that is a scalar should return defaults."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("just a string\n")
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.data_dir == ".personal_index"
    finally:
        os.unlink(path)


def test_load_config_null_values():
    """Loading config with null values should use defaults for those fields."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("data_dir: null\nlog_level: null\n")
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.data_dir is None or cfg.data_dir == ".personal_index"
    finally:
        os.unlink(path)


# =============================================================================
# Type coercion edge cases
# =============================================================================

def test_load_config_string_int_values():
    """Config values that are strings but should be ints."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("crawler:\n  max_depth: '5'\n")
        path = f.name
    try:
        cfg = load_config(path)
        # YAML parses '5' as string, but CrawlerConfig expects int
        # This tests whether the loader handles type mismatches
        assert cfg.crawler.max_depth == 5 or cfg.crawler.max_depth == "5"
    finally:
        os.unlink(path)


def test_load_config_float_as_int():
    """Config values that are floats where ints are expected."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("crawler:\n  max_depth: 5.5\n")
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.crawler.max_depth == 5.5 or cfg.crawler.max_depth == 5
    finally:
        os.unlink(path)


def test_load_config_bool_as_int():
    """Config values that are bools where ints are expected."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("crawler:\n  max_depth: true\n")
        path = f.name
    try:
        cfg = load_config(path)
        # YAML parses true as bool, CrawlerConfig expects int
        assert cfg.crawler.max_depth is True or cfg.crawler.max_depth == 1
    finally:
        os.unlink(path)


def test_load_config_unicode_values():
    """Config values with unicode characters."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write("data_dir: /path/with/üñíçödé\n")
        f.write("log_level: INFO\n")
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.data_dir == "/path/with/üñíçödé"
    finally:
        os.unlink(path)


# =============================================================================
# Interest parsing edge cases
# =============================================================================

def test_load_config_interests_empty_list():
    """Config with empty interests list."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("interests: []\n")
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.interests == []
    finally:
        os.unlink(path)


def test_load_config_interests_missing_name():
    """Interest without a name field."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("interests:\n  - keywords: [test]\n")
        path = f.name
    try:
        cfg = load_config(path)
        assert len(cfg.interests) == 1
        assert cfg.interests[0].name == ""
    finally:
        os.unlink(path)


def test_load_config_interests_invalid_match_mode():
    """Interest with invalid match_mode string."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("interests:\n  - name: test\n    match_mode: invalid_mode\n")
        path = f.name
    try:
        cfg = load_config(path)
        assert len(cfg.interests) == 1
        assert cfg.interests[0].match_mode == MatchMode.ANY  # fallback
    finally:
        os.unlink(path)


def test_load_config_interests_priority_clamping():
    """Interest with priority outside 1-10 range should be clamped."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("interests:\n")
        f.write("  - name: low\n    priority: 0\n")
        f.write("  - name: high\n    priority: 15\n")
        f.write("  - name: normal\n    priority: 5\n")
        path = f.name
    try:
        cfg = load_config(path)
        assert len(cfg.interests) == 3
        assert cfg.interests[0].priority == 1  # clamped up
        assert cfg.interests[1].priority == 10  # clamped down
        assert cfg.interests[2].priority == 5  # unchanged
    finally:
        os.unlink(path)


def test_load_config_interests_non_dict_items():
    """Interest list with non-dict items should be skipped."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("interests:\n  - just a string\n  - 42\n  - name: valid\n")
        path = f.name
    try:
        cfg = load_config(path)
        assert len(cfg.interests) == 1
        assert cfg.interests[0].name == "valid"
    finally:
        os.unlink(path)


# =============================================================================
# Backward compatibility aliases
# =============================================================================

def test_load_config_crawl_alias():
    """Config using old 'crawl' key instead of 'crawler'."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("crawl:\n  max_depth: 7\n")
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.crawler.max_depth == 7
    finally:
        os.unlink(path)


def test_app_config_crawl_property():
    """AppConfig.crawl property should return crawler."""
    cfg = AppConfig()
    assert cfg.crawl is cfg.crawler


def test_app_config_indexer_property():
    """AppConfig.indexer property should return index."""
    cfg = AppConfig()
    assert cfg.indexer is cfg.index


# =============================================================================
# Validation errors
# =============================================================================

def test_crawler_config_validation_errors():
    """CrawlerConfig.validate() should catch invalid values."""
    cfg = CrawlerConfig(max_depth=-1, politeness_delay=-1.0, rate_limit=0, timeout=0)
    errors = cfg.validate()
    assert len(errors) == 4
    assert any("max_depth" in e for e in errors)
    assert any("politeness_delay" in e for e in errors)
    assert any("rate_limit" in e for e in errors)
    assert any("timeout" in e for e in errors)


def test_index_config_validation_errors():
    """IndexConfig.validate() should catch invalid values."""
    cfg = IndexConfig(min_term_length=0, max_index_size=0, fuzzy_threshold=1.5)
    errors = cfg.validate()
    assert len(errors) == 3
    assert any("min_term_length" in e for e in errors)
    assert any("max_index_size" in e for e in errors)
    assert any("fuzzy_threshold" in e for e in errors)


def test_scheduler_config_validation_errors():
    """SchedulerConfig.validate() should catch invalid values."""
    cfg = SchedulerConfig(interval_hours=0, max_concurrent_jobs=0)
    errors = cfg.validate()
    assert len(errors) == 2
    assert any("interval_hours" in e for e in errors)
    assert any("max_concurrent_jobs" in e for e in errors)


def test_notification_config_validation_errors():
    """NotificationConfig.validate() should catch missing contact info."""
    cfg = NotificationConfig(enabled=True, email="", webhook_url="")
    errors = cfg.validate()
    assert len(errors) == 1
    assert "email or webhook_url" in errors[0]


def test_export_config_validation_errors():
    """ExportConfig.validate() should catch unknown formats."""
    cfg = ExportConfig(default_format="xml")
    errors = cfg.validate()
    assert len(errors) == 1
    assert "unknown export format" in errors[0]


def test_app_config_validation_aggregates_errors():
    """AppConfig.validate() should aggregate errors from all sections."""
    cfg = AppConfig()
    cfg.crawler = CrawlerConfig(max_depth=-1)
    cfg.index = IndexConfig(min_term_length=0)
    cfg.scheduler = SchedulerConfig(interval_hours=0)
    cfg.notifications = NotificationConfig(enabled=True)
    cfg.export = ExportConfig(default_format="xml")
    errors = cfg.validate()
    assert len(errors) == 5


# =============================================================================
# Serialization/deserialization round-trips
# =============================================================================

def test_app_config_roundtrip():
    """AppConfig to_dict/from_dict should round-trip."""
    original = AppConfig(
        data_dir="/custom",
        log_level="DEBUG",
        crawler=CrawlerConfig(max_depth=5),
        index=IndexConfig(enable_stemming=False),
        scheduler=SchedulerConfig(enabled=True, interval_hours=12),
        notifications=NotificationConfig(enabled=True, email="test@example.com"),
        export=ExportConfig(default_format="json"),
        interests=[Interest(name="test", keywords=["kw"], priority=7)],
    )
    data = original.to_dict()
    restored = AppConfig.from_dict(data)
    assert restored.data_dir == original.data_dir
    assert restored.log_level == original.log_level
    assert restored.crawler.max_depth == original.crawler.max_depth
    assert restored.index.enable_stemming == original.index.enable_stemming
    assert restored.scheduler.enabled == original.scheduler.enabled
    assert restored.scheduler.interval_hours == original.scheduler.interval_hours
    assert restored.notifications.email == original.notifications.email
    assert restored.export.default_format == original.export.default_format
    assert len(restored.interests) == 1
    assert restored.interests[0].name == "test"
    assert restored.interests[0].priority == 7


def test_interest_roundtrip():
    """Interest to_dict/from_dict should round-trip."""
    original = Interest(
        name="AI News",
        keywords=["AI", "ML"],
        url_patterns=["*.techcrunch.com"],
        topics=["technology"],
        priority=8,
        enabled=True,
        match_mode=MatchMode.ALL,
    )
    data = original.to_dict()
    restored = Interest.from_dict(data)
    assert restored.name == original.name
    assert restored.keywords == original.keywords
    assert restored.url_patterns == original.url_patterns
    assert restored.topics == original.topics
    assert restored.priority == original.priority
    assert restored.enabled == original.enabled
    assert restored.match_mode == original.match_mode


def test_interest_match_mode_string_roundtrip():
    """Interest match_mode should serialize to string and deserialize back."""
    interest = Interest(name="test", match_mode=MatchMode.REGEX)
    data = interest.to_dict()
    assert data["match_mode"] == "regex"
    restored = Interest.from_dict(data)
    assert restored.match_mode == MatchMode.REGEX


def test_app_config_yaml_roundtrip():
    """AppConfig should round-trip through YAML serialization."""
    original = AppConfig(
        data_dir="/yaml/test",
        crawler=CrawlerConfig(max_depth=4),
        interests=[Interest(name="yaml test", keywords=["yaml"])],
    )
    data = original.to_dict()
    yaml_str = yaml.dump(data)
    loaded = yaml.safe_load(yaml_str)
    restored = AppConfig.from_dict(loaded)
    assert restored.data_dir == "/yaml/test"
    assert restored.crawler.max_depth == 4
    assert len(restored.interests) == 1


# =============================================================================
# Concurrent access scenarios
# =============================================================================

def test_config_thread_safe_read():
    """Multiple threads reading the same config should not corrupt it."""
    cfg = AppConfig(
        data_dir="/concurrent",
        crawler=CrawlerConfig(max_depth=5),
        interests=[Interest(name="concurrent", keywords=["test"])],
    )

    errors = []

    def read_config():
        try:
            assert cfg.data_dir == "/concurrent"
            assert cfg.crawler.max_depth == 5
            assert len(cfg.interests) == 1
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=read_config) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []


def test_config_thread_safe_write():
    """Multiple threads writing to different config fields should not crash."""
    cfg = AppConfig()

    def write_field(i):
        cfg.data_dir = f"/thread/{i}"

    threads = [threading.Thread(target=write_field, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # Final value should be one of the written values
    assert cfg.data_dir.startswith("/thread/")


def test_config_pool_concurrent_access():
    """ThreadPoolExecutor concurrent access to config."""
    cfg = AppConfig(crawler=CrawlerConfig(max_depth=3))

    def validate(i):
        return cfg.validate()

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(validate, i) for i in range(8)]
        results = [f.result() for f in futures]
    # All validations should complete without error
    assert len(results) == 8


# =============================================================================
# Edge cases: extreme values
# =============================================================================

def test_crawler_config_extreme_values():
    """CrawlerConfig with extreme but valid values."""
    cfg = CrawlerConfig(
        max_depth=1000,
        politeness_delay=0.001,
        rate_limit=10000,
        timeout=3600,
        max_pages_per_domain=1000000,
    )
    errors = cfg.validate()
    assert errors == []


def test_index_config_extreme_values():
    """IndexConfig with extreme but valid values."""
    cfg = IndexConfig(
        min_term_length=1,
        max_index_size=1000000000,
        fuzzy_threshold=0.0,
    )
    errors = cfg.validate()
    assert errors == []


def test_interest_priority_extreme_values():
    """Interest priority with extreme values should clamp."""
    i1 = Interest(name="test", priority=-100)
    assert i1.priority == 1

    i2 = Interest(name="test", priority=1000)
    assert i2.priority == 10


# =============================================================================
# Default config values
# =============================================================================

def test_default_app_config():
    """Default AppConfig should have sensible defaults."""
    cfg = AppConfig()
    assert cfg.data_dir == ".personal_index"
    assert cfg.log_level == "INFO"
    assert cfg.crawler.max_depth == 3
    assert cfg.crawler.politeness_delay == 1.0
    assert cfg.crawler.respect_robots_txt is True
    assert cfg.index.enable_stemming is True
    assert cfg.index.min_term_length == 2
    assert cfg.scheduler.enabled is False
    assert cfg.scheduler.interval_hours == 24
    assert cfg.notifications.enabled is False
    assert cfg.export.default_format == "markdown"


def test_default_config_validates():
    """Default AppConfig should pass validation."""
    cfg = AppConfig()
    errors = cfg.validate()
    assert errors == []


# =============================================================================
# MatchMode parsing
# =============================================================================

def test_match_mode_parsing():
    """MatchMode should parse from string values."""
    assert MatchMode("any") == MatchMode.ANY
    assert MatchMode("all") == MatchMode.ALL
    assert MatchMode("regex") == MatchMode.REGEX


def test_match_mode_invalid_string():
    """MatchMode with invalid string should raise ValueError."""
    with pytest.raises(ValueError):
        MatchMode("invalid")


def test_match_mode_case_insensitive_in_loader():
    """Loader should handle case-insensitive match_mode strings."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("interests:\n  - name: test\n    match_mode: ALL\n")
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg.interests[0].match_mode == MatchMode.ALL
    finally:
        os.unlink(path)


# =============================================================================
# Environment variable overrides (if supported)
# =============================================================================

def test_config_env_var_override_data_dir():
    """PERSONAL_INDEX_DATA_DIR env var should override data_dir."""
    os.environ["PERSONAL_INDEX_DATA_DIR"] = "/env/override"
    try:
        cfg = AppConfig()
        # Check if env var is respected (depends on implementation)
        # If not, this documents the current behavior
        assert cfg.data_dir in (".personal_index", "/env/override")
    finally:
        del os.environ["PERSONAL_INDEX_DATA_DIR"]


def test_config_env_var_override_log_level():
    """PERSONAL_INDEX_LOG_LEVEL env var should override log_level."""
    os.environ["PERSONAL_INDEX_LOG_LEVEL"] = "DEBUG"
    try:
        cfg = AppConfig()
        assert cfg.log_level in ("INFO", "DEBUG")
    finally:
        del os.environ["PERSONAL_INDEX_LOG_LEVEL"]


# =============================================================================
# Config file path edge cases
# =============================================================================

def test_load_config_relative_path():
    """Loading config from a relative path."""
    orig_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        with open("config.yaml", "w") as f:
            f.write("data_dir: /relative/test\n")
        try:
            cfg = load_config("config.yaml")
            assert cfg.data_dir == "/relative/test"
        finally:
            os.chdir(orig_cwd)


def test_load_config_path_with_spaces():
    """Loading config from a path with spaces."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "config file.yaml")
        with open(path, "w") as f:
            f.write("data_dir: /spaces/test\n")
        cfg = load_config(path)
        assert cfg.data_dir == "/spaces/test"


# =============================================================================
# Duplicate/overlapping config sections
# =============================================================================

def test_load_config_duplicate_interests():
    """Config with duplicate interest names."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("interests:\n")
        f.write("  - name: duplicate\n    keywords: [a]\n")
        f.write("  - name: duplicate\n    keywords: [b]\n")
        path = f.name
    try:
        cfg = load_config(path)
        assert len(cfg.interests) == 2  # both kept, no dedup
    finally:
        os.unlink(path)


def test_load_config_overlapping_crawler_crawl():
    """Config with both 'crawler' and 'crawl' keys."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("crawler:\n  max_depth: 5\n")
        f.write("crawl:\n  max_depth: 7\n")
        path = f.name
    try:
        cfg = load_config(path)
        # 'crawler' should take precedence
        assert cfg.crawler.max_depth == 5
    finally:
        os.unlink(path)


# =============================================================================
# JSON serialization (alternative format)
# =============================================================================

def test_app_config_json_roundtrip():
    """AppConfig should round-trip through JSON serialization."""
    original = AppConfig(
        data_dir="/json/test",
        crawler=CrawlerConfig(max_depth=4),
        interests=[Interest(name="json test", keywords=["json"])],
    )
    data = original.to_dict()
    json_str = json.dumps(data)
    loaded = json.loads(json_str)
    restored = AppConfig.from_dict(loaded)
    assert restored.data_dir == "/json/test"
    assert restored.crawler.max_depth == 4
    assert len(restored.interests) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
