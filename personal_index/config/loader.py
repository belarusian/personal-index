"""Configuration loader for personal-index."""

from __future__ import annotations

import logging
import os

import yaml

from personal_index.config.models import AppConfig

logger = logging.getLogger(__name__)


def load_config(path: str) -> AppConfig:
    """Load configuration from a YAML file.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        AppConfig instance with loaded values.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        yaml.YAMLError: If the config file is invalid YAML.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    if data is None:
        data = {}

    return AppConfig.from_dict(data)


def save_config(config: AppConfig, path: str) -> None:
    """Save configuration to a YAML file.

    Args:
        config: AppConfig instance to save.
        path: Path to write the YAML file.
    """
    data = config.to_dict()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    logger.info("Config saved to %s", path)


def validate_config(config: AppConfig) -> list[str]:
    """Validate configuration and return list of errors.

    Args:
        config: AppConfig instance to validate.

    Returns:
        List of error messages. Empty if valid.
    """
    return config.validate()


def get_default_config() -> AppConfig:
    """Return a default AppConfig instance.

    Returns:
        AppConfig with all default values.
    """
    return AppConfig()


def merge_configs(base: AppConfig, override: dict) -> AppConfig:
    """Merge an override dict into a base config.

    Args:
        base: Base AppConfig instance.
        override: Dictionary of values to override.

    Returns:
        New AppConfig with merged values.
    """
    base_dict = base.to_dict()
    _deep_merge(base_dict, override)
    return AppConfig.from_dict(base_dict)


def _deep_merge(base: dict, override: dict) -> None:
    """Recursively merge override into base dict."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
