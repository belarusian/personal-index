"""Batch processing for content operations in personal-index.

Provides utilities for processing content items in batches,
with support for parallel execution, error handling, and
progress tracking.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

BatchProcessorFn = Callable[[list[dict[str, Any]]], list[dict[str, Any]]]


@dataclass
class BatchResult:
    """Result of a batch processing operation.

    Attributes:
        batch_id: Unique identifier for the batch.
        total_items: Total items in the batch.
        processed: Number of items successfully processed.
        failed: Number of items that failed.
        errors: List of error details.
        started_at: When processing started.
        completed_at: When processing completed.
        duration_seconds: Processing duration.
        output: Processed output items.
    """

    batch_id: str
    total_items: int
    processed: int = 0
    failed: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float = 0.0
    output: list[dict[str, Any]] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_items == 0:
            return 0.0
        return self.processed / self.total_items

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "batch_id": self.batch_id,
            "total_items": self.total_items,
            "processed": self.processed,
            "failed": self.failed,
            "errors": self.errors,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "success_rate": round(self.success_rate, 4),
        }


class BatchProcessor:
    """Processes content items in configurable batch sizes.

    Supports custom processing functions, error handling,
    and progress callbacks.
    """

    def __init__(
        self,
        batch_size: int = 100,
        processor: BatchProcessorFn | None = None,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> None:
        self.batch_size = batch_size
        self.processor = processor or self._default_processor
        self.on_progress = on_progress
        self._batch_counter = 0

    def process(
        self,
        items: list[dict[str, Any]],
    ) -> BatchResult:
        """Process all items in batches.

        Args:
            items: List of content items to process.

        Returns:
            BatchResult with processing statistics.
        """
        self._batch_counter += 1
        batch_id = f"batch-{self._batch_counter}"
        result = BatchResult(
            batch_id=batch_id,
            total_items=len(items),
            started_at=datetime.now(timezone.utc),
        )

        total = len(items)
        processed_count = 0

        for i in range(0, total, self.batch_size):
            batch = items[i : i + self.batch_size]
            try:
                output = self.processor(batch)
                result.output.extend(output)
                result.processed += len(batch)
            except ValueError as e:
                result.failed += len(batch)
                result.errors.append({
                    "batch_start": i,
                    "batch_size": len(batch),
                    "error": str(e),
                })

            processed_count += len(batch)
            if self.on_progress:
                self.on_progress(processed_count, total)

        result.completed_at = datetime.now(timezone.utc)
        if result.started_at:
            result.duration_seconds = (
                result.completed_at - result.started_at
            ).total_seconds()

        return result

    def process_with_retry(
        self,
        items: list[dict[str, Any]],
        max_retries: int = 3,
    ) -> BatchResult:
        """Process items with retry logic for failed batches.

        Args:
            items: List of content items.
            max_retries: Maximum retry attempts per batch.

        Returns:
            BatchResult with processing statistics.
        """
        self._batch_counter += 1
        batch_id = f"batch-{self._batch_counter}"
        result = BatchResult(
            batch_id=batch_id,
            total_items=len(items),
            started_at=datetime.now(timezone.utc),
        )

        total = len(items)
        processed_count = 0

        for i in range(0, total, self.batch_size):
            batch = items[i : i + self.batch_size]

            for attempt in range(max_retries):
                try:
                    output = self.processor(batch)
                    result.output.extend(output)
                    result.processed += len(batch)
                    break
                except ValueError as e:
                    if attempt == max_retries - 1:
                        result.failed += len(batch)
                        result.errors.append({
                            "batch_start": i,
                            "attempts": attempt + 1,
                            "error": str(e),
                        })

            processed_count += len(batch)
            if self.on_progress:
                self.on_progress(processed_count, total)

        result.completed_at = datetime.now(timezone.utc)
        if result.started_at:
            result.duration_seconds = (
                result.completed_at - result.started_at
            ).total_seconds()

        return result

    def _default_processor(
        self,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Default processor that returns items unchanged."""
        return items

    def process_item_by_item(
        self,
        items: list[dict[str, Any]],
        item_processor: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> BatchResult:
        """Process items individually with per-item error handling.

        Args:
            items: List of content items.
            item_processor: Function to process each item.

        Returns:
            BatchResult with processing statistics.
        """
        self._batch_counter += 1
        batch_id = f"batch-{self._batch_counter}"
        result = BatchResult(
            batch_id=batch_id,
            total_items=len(items),
            started_at=datetime.now(timezone.utc),
        )

        for i, item in enumerate(items):
            try:
                output = item_processor(item)
                result.output.append(output)
                result.processed += 1
            except ValueError as e:
                result.failed += 1
                result.errors.append({
                    "item_index": i,
                    "item_id": item.get("id", "unknown"),
                    "error": str(e),
                })

            if self.on_progress:
                self.on_progress(i + 1, len(items))

        result.completed_at = datetime.now(timezone.utc)
        if result.started_at:
            result.duration_seconds = (
                result.completed_at - result.started_at
            ).total_seconds()

        return result
