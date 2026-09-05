"""Batch processing for content operations in personal-index.

Provides utilities for processing content items in batches,
with support for error handling and progress tracking.
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

        Increments the batch counter, builds a BatchResult (batch_id,
        total_items, started_at), chunks items by ``batch_size``, runs
        each chunk through ``_process_single_batch``, reports progress
        via ``on_progress``, finalizes timing, and returns the result.
        """
        self._batch_counter += 1
        result = BatchResult(
            batch_id=f"batch-{self._batch_counter}",
            total_items=len(items),
            started_at=datetime.now(timezone.utc),
        )

        total = len(items)
        processed_count = 0

        for i in range(0, total, self.batch_size):
            batch = items[i : i + self.batch_size]
            self._process_single_batch(batch, i, result)

            processed_count += len(batch)
            if self.on_progress:
                self.on_progress(processed_count, total)

        self._finalize_result(result)
        return result

    def _process_single_batch(
        self,
        batch: list[dict[str, Any]],
        batch_start: int,
        result: BatchResult,
    ) -> None:
        """Run one batch through the processor, recording success or failure.

        On success, extends ``result.output`` with the processor output
        and increments ``result.processed`` by the batch length. On
        ``ValueError``, increments ``result.failed`` by the batch length
        and appends an error entry keyed by ``batch_start``,
        ``batch_size`` and ``error``.
        """
        try:
            output = self.processor(batch)
            result.output.extend(output)
            result.processed += len(batch)
        except ValueError as e:
            result.failed += len(batch)
            result.errors.append({
                "batch_start": batch_start,
                "batch_size": len(batch),
                "error": str(e),
            })

    def process_with_retry(
        self,
        items: list[dict[str, Any]],
        max_retries: int = 3,
    ) -> BatchResult:
        """Process all items in batches, retrying failed batches.

        Like ``process``, but each chunk goes through
        ``_try_process_batch``, which retries the processor up to
        ``max_retries`` times before recording a failure.
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
            self._try_process_batch(batch, max_retries, i, result)

            processed_count += len(batch)
            if self.on_progress:
                self.on_progress(processed_count, total)

        self._finalize_result(result)
        return result

    def _try_process_batch(
        self,
        batch: list[dict[str, Any]],
        max_retries: int,
        batch_start: int,
        result: BatchResult,
    ) -> None:
        """Try to process a single batch with retries."""
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
                        "batch_start": batch_start,
                        "attempts": attempt + 1,
                        "error": str(e),
                    })

    def _finalize_result(self, result: BatchResult) -> None:
        """Set completion timestamp and duration on result."""
        result.completed_at = datetime.now(timezone.utc)
        if result.started_at:
            result.duration_seconds = (
                result.completed_at - result.started_at
            ).total_seconds()

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

        Runs each item through ``item_processor`` (not batched),
        accumulating per-item output, processed and failed counts and
        error entries, reports progress per item, finalizes timing, and
        returns the result.
        """
        self._batch_counter += 1
        result = BatchResult(
            batch_id=f"batch-{self._batch_counter}",
            total_items=len(items),
            started_at=datetime.now(timezone.utc),
        )
        for i, item in enumerate(items):
            self._process_single_item(item, i, item_processor, result)
            if self.on_progress:
                self.on_progress(i + 1, len(items))
        self._finalize_result(result)
        return result

    def _process_single_item(
        self, item: dict[str, Any], idx: int,
        processor: Callable[[dict[str, Any]], dict[str, Any]],
        result: BatchResult,
    ) -> None:
        """Run one item through the processor, recording success or failure.

        On success, appends the processor output to ``result.output``
        and increments ``result.processed`` by 1. On ``ValueError``,
        increments ``result.failed`` by 1 and appends an error entry
        keyed by ``item_index``, ``item_id`` and ``error``.
        """
        try:
            output = processor(item)
            result.output.append(output)
            result.processed += 1
        except ValueError as e:
            result.failed += 1
            result.errors.append({
                "item_index": idx,
                "item_id": item.get("id", "unknown"),
                "error": str(e),
            })
