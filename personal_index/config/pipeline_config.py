"""Pipeline configuration loader for personal-index."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class PipelineStepConfig:
    """Configuration for a single pipeline step."""
    name: str = ""
    enabled: bool = True


@dataclass
class PipelineConfig:
    """Configuration for the content processing pipeline."""
    enabled: bool = True
    steps: list[PipelineStepConfig] = field(default_factory=list)
    min_score_threshold: float = 0.0
    min_content_length: int = 100
    max_pages: int = 100
    crawl_timeout: int = 30
    politeness_delay: float = 1.0

    def get_enabled_steps(self) -> list[str]:
        """Return names of enabled steps."""
        return [s.name for s in self.steps if s.enabled]

    def is_step_enabled(self, name: str) -> bool:
        """Check if a specific step is enabled.

        If the step is not explicitly configured, it defaults to enabled.
        """
        for step in self.steps:
            if step.name == name:
                return step.enabled
        return True  # default to enabled if not configured

    def disable_step(self, name: str) -> None:
        """Disable a specific step by name."""
        for step in self.steps:
            if step.name == name:
                step.enabled = False
                return
        # If step not in list, add it as disabled
        self.steps.append(PipelineStepConfig(name=name, enabled=False))

    def enable_step(self, name: str) -> None:
        """Enable a specific step by name."""
        for step in self.steps:
            if step.name == name:
                step.enabled = True
                return
        # If step not in list, add it as enabled
        self.steps.append(PipelineStepConfig(name=name, enabled=True))


def load_pipeline_config(config_path: str = "config.yaml") -> PipelineConfig:
    """Load pipeline configuration from a YAML file.

    Args:
        config_path: Path to the configuration file.

    Returns:
        A PipelineConfig instance with loaded settings.
    """
    path = Path(config_path)
    if not path.exists():
        return PipelineConfig()

    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}

    pipeline_data = data.get("pipeline", {})
    steps_data = pipeline_data.get("steps", [])
    steps = [
        PipelineStepConfig(name=s.get("name", ""), enabled=s.get("enabled", True))
        for s in steps_data if isinstance(s, dict)
    ]

    # Load crawler settings into pipeline config
    crawler_data = data.get("crawler", {})

    return PipelineConfig(
        enabled=pipeline_data.get("enabled", True),
        steps=steps,
        min_score_threshold=pipeline_data.get("min_score_threshold", 0.0),
        min_content_length=pipeline_data.get("min_content_length", 100),
        max_pages=crawler_data.get("max_pages", 100),
        crawl_timeout=crawler_data.get("timeout", 30),
        politeness_delay=crawler_data.get("politeness_delay", 1.0),
    )
