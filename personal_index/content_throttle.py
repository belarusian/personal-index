"""Throttle concurrent operations in the personal index.

Provides semaphore-based throttling for limiting concurrent
content processing operations with queue management.
"""

from __future__ import annotations

import time
import threading
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ThrottleConfig:
    """Configuration for operation throttling."""

    max_concurrent: int = 5
    timeout_seconds: float = 30.0
    queue_size: int = 100


@dataclass
class ThrottleResult:
    """Result of a throttle acquisition attempt."""

    acquired: bool
    wait_time: float = 0.0


class _ThrottleSlot:
    """Throttle control for a single operation type."""

    def __init__(self, config: ThrottleConfig) -> None:
        self._semaphore = threading.Semaphore(config.max_concurrent)
        self._queue_size = config.queue_size
        self._timeout = config.timeout_seconds
        self._max_concurrent = config.max_concurrent
        self._active_count = 0
        self._total_acquired = 0
        self._total_rejected = 0
        self._total_waited = 0
        self._total_wait_time = 0.0
        self._lock = threading.Lock()

    def acquire(self, timeout: float | None = None) -> ThrottleResult:
        """Try to acquire a throttle slot.

        Args:
            timeout: Override timeout in seconds.

        Returns:
            ThrottleResult indicating if slot was acquired.
        """
        effective_timeout = timeout if timeout is not None else self._timeout
        start = time.monotonic()

        acquired = self._semaphore.acquire(timeout=effective_timeout)
        wait_time = time.monotonic() - start

        with self._lock:
            if acquired:
                self._active_count += 1
                self._total_acquired += 1
                if wait_time > 0.01:
                    self._total_waited += 1
                    self._total_wait_time += wait_time
                return ThrottleResult(acquired=True, wait_time=round(wait_time, 4))
            else:
                self._total_rejected += 1
                return ThrottleResult(acquired=False, wait_time=round(wait_time, 4))

    def release(self) -> None:
        """Release a throttle slot."""
        with self._lock:
            self._active_count = max(0, self._active_count - 1)
        self._semaphore.release()

    @property
    def active_count(self) -> int:
        with self._lock:
            return self._active_count

    @property
    def available_slots(self) -> int:
        with self._lock:
            return max(0, self._max_concurrent - self._active_count)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "active": self._active_count,
                "max_concurrent": self._max_concurrent,
                "available": self.available_slots,
                "total_acquired": self._total_acquired,
                "total_rejected": self._total_rejected,
                "total_waited": self._total_waited,
                "total_wait_time": round(self._total_wait_time, 4),
            }


class ContentThrottle:
    """Throttle concurrent content operations.

    Manages per-operation-type throttling with configurable
    concurrency limits and timeouts.
    """

    def __init__(self, default_config: Optional[ThrottleConfig] = None) -> None:
        self._default_config = default_config or ThrottleConfig()
        self._configs: dict[str, ThrottleConfig] = {}
        self._slots: dict[str, _ThrottleSlot] = {}
        self._lock = threading.Lock()

    def set_config(self, operation: str, config: ThrottleConfig) -> None:
        """Set throttle config for a specific operation type.

        Args:
            operation: Operation name (e.g., "extract", "index").
            config: Throttle configuration.
        """
        with self._lock:
            self._configs[operation] = config
            self._slots[operation] = _ThrottleSlot(config)

    def _get_slot(self, operation: str) -> _ThrottleSlot:
        if operation not in self._slots:
            config = self._configs.get(operation, self._default_config)
            self._slots[operation] = _ThrottleSlot(config)
        return self._slots[operation]

    def acquire(self, operation: str, timeout: float | None = None) -> ThrottleResult:
        """Acquire a throttle slot for an operation.

        Args:
            operation: Operation name.
            timeout: Optional timeout override.

        Returns:
            ThrottleResult with acquisition status.
        """
        slot = self._get_slot(operation)
        return slot.acquire(timeout=timeout)

    def release(self, operation: str) -> None:
        """Release a throttle slot.

        Args:
            operation: Operation name.
        """
        slot = self._get_slot(operation)
        slot.release()

    def acquire_or_wait(self, operation: str, timeout: float | None = None) -> bool:
        """Acquire a slot, waiting if necessary.

        Args:
            operation: Operation name.
            timeout: Optional timeout override.

        Returns:
            True if slot was acquired, False if timed out.
        """
        result = self.acquire(operation, timeout=timeout)
        return result.acquired

    def get_active_count(self, operation: str) -> int:
        """Get number of active operations.

        Args:
            operation: Operation name.

        Returns:
            Number of currently active operations.
        """
        slot = self._get_slot(operation)
        return slot.active_count

    def get_available_slots(self, operation: str) -> int:
        """Get number of available slots.

        Args:
            operation: Operation name.

        Returns:
            Number of available slots.
        """
        slot = self._get_slot(operation)
        return slot.available_slots

    def stats(self, operation: Optional[str] = None) -> dict[str, Any]:
        """Get throttle statistics.

        Args:
            operation: Optional specific operation to get stats for.

        Returns:
            Statistics dictionary.
        """
        if operation:
            slot = self._slots.get(operation)
            if slot:
                return {"operation": operation, **slot.stats()}
            return {"operation": operation, "active": 0}

        return {
            "tracked_operations": len(self._slots),
            "operations": {k: v.stats() for k, v in self._slots.items()},
        }

    def reset(self, operation: str) -> None:
        """Reset throttle for an operation.

        Args:
            operation: Operation name to reset.
        """
        with self._lock:
            config = self._configs.get(operation, self._default_config)
            self._slots[operation] = _ThrottleSlot(config)

    def reset_all(self) -> None:
        """Reset all throttle slots."""
        with self._lock:
            for op, config in self._configs.items():
                self._slots[op] = _ThrottleSlot(config)
            default_ops = set(self._slots.keys()) - set(self._configs.keys())
            for op in default_ops:
                self._slots[op] = _ThrottleSlot(self._default_config)
