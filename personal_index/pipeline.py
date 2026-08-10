"""Content processing pipeline for sequential transformations."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class PipelineStep:
    """A single step in the processing pipeline."""

    name: str
    handler: Callable[[dict], dict]
    enabled: bool = True
    on_error: str = "continue"  # "continue", "skip", "stop"

    def execute(self, data: dict) -> dict:
        """Execute this step on the data."""
        if not self.enabled:
            return data
        try:
            return self.handler(data)
        except Exception as e:
            logger.warning("Pipeline step '%s' failed: %s", self.name, e)
            if self.on_error == "stop":
                raise
            return data


@dataclass
class PipelineResult:
    """Result of running a pipeline."""

    success: bool
    data: dict
    steps_executed: int = 0
    steps_failed: int = 0
    errors: list[str] = field(default_factory=list)


class ContentPipeline:
    """Sequential pipeline for processing content through multiple steps."""

    def __init__(self, name: str = "default"):
        self.name = name
        self._steps: list[PipelineStep] = []

    def add_step(self, name: str, handler: Callable[[dict], dict],
                 enabled: bool = True, on_error: str = "continue") -> ContentPipeline:
        """Add a processing step to the pipeline."""
        self._steps.append(PipelineStep(
            name=name,
            handler=handler,
            enabled=enabled,
            on_error=on_error,
        ))
        return self

    def remove_step(self, name: str) -> bool:
        """Remove a step by name."""
        for i, step in enumerate(self._steps):
            if step.name == name:
                self._steps.pop(i)
                return True
        return False

    def disable_step(self, name: str) -> bool:
        """Disable a step by name."""
        for step in self._steps:
            if step.name == name:
                step.enabled = False
                return True
        return False

    def enable_step(self, name: str) -> bool:
        """Enable a step by name."""
        for step in self._steps:
            if step.name == name:
                step.enabled = True
                return True
        return False

    def run(self, data: dict) -> PipelineResult:
        """Run the pipeline on the given data."""
        errors = []
        steps_executed = 0
        steps_failed = 0

        for step in self._steps:
            if not step.enabled:
                continue
            try:
                data = step.handler(data)
                steps_executed += 1
            except Exception as e:
                steps_failed += 1
                errors.append(f"Step '{step.name}': {e}")
                if step.on_error == "stop":
                    break
                # On continue, keep data as-is for this step

        return PipelineResult(
            success=steps_failed == 0,
            data=data,
            steps_executed=steps_executed,
            steps_failed=steps_failed,
            errors=errors,
        )

    @property
    def step_count(self) -> int:
        """Total number of steps in the pipeline."""
        return len(self._steps)

    @property
    def enabled_steps(self) -> list[str]:
        """Names of currently enabled steps."""
        return [s.name for s in self._steps if s.enabled]

    def get_step(self, name: str) -> Optional[PipelineStep]:
        """Get a step by name.

        Args:
            name: The step name.

        Returns:
            The PipelineStep, or None if not found.
        """
        for step in self._steps:
            if step.name == name:
                return step
        return None

    def clear(self) -> None:
        """Remove all steps from the pipeline."""
        self._steps.clear()
