"""Tests for the content batch processing module."""

from datetime import datetime, timezone

from personal_index.content_batch import BatchProcessor, BatchResult


class TestBatchResult:
    def test_create(self) -> None:
        result = BatchResult(batch_id="b1", total_items=10)
        assert result.processed == 0
        assert result.failed == 0
        assert result.success_rate == 0.0

    def test_success_rate(self) -> None:
        result = BatchResult(batch_id="b1", total_items=10)
        result.processed = 8
        result.failed = 2
        assert result.success_rate == 0.8

    def test_to_dict(self) -> None:
        result = BatchResult(
            batch_id="b1",
            total_items=10,
            processed=8,
            started_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            completed_at=datetime(2024, 1, 1, 0, 0, 5, tzinfo=timezone.utc),
        )
        d = result.to_dict()
        assert d["batch_id"] == "b1"
        assert d["success_rate"] == 0.8


class TestBatchProcessor:
    def setup_method(self) -> None:
        self.items = [{"id": str(i), "value": i} for i in range(25)]

    def test_process_default(self) -> None:
        processor = BatchProcessor(batch_size=10)
        result = processor.process(self.items)
        assert result.total_items == 25
        assert result.processed == 25
        assert result.failed == 0

    def test_process_custom(self) -> None:
        def double_value(batch):
            return [{"id": i["id"], "value": i["value"] * 2} for i in batch]

        processor = BatchProcessor(batch_size=10, processor=double_value)
        result = processor.process(self.items)
        assert result.processed == 25
        assert result.output[0]["value"] == 0
        assert result.output[5]["value"] == 10

    def test_process_error(self) -> None:
        def failing_processor(batch):
            raise ValueError("Processing failed")

        processor = BatchProcessor(batch_size=10, processor=failing_processor)
        result = processor.process(self.items)
        assert result.failed == 25
        assert len(result.errors) > 0

    def test_process_progress(self) -> None:
        progress_calls = []

        def on_progress(current, total):
            progress_calls.append((current, total))

        processor = BatchProcessor(
            batch_size=10, on_progress=on_progress,
        )
        processor.process(self.items)
        assert len(progress_calls) == 3  # 3 batches
        assert progress_calls[-1] == (25, 25)

    def test_process_with_retry_success(self) -> None:
        call_count = [0]

        def flaky_processor(batch):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ValueError("Temporary failure")
            return batch

        processor = BatchProcessor(
            batch_size=25, processor=flaky_processor,
        )
        result = processor.process_with_retry(self.items, max_retries=3)
        assert result.processed == 25

    def test_process_with_retry_exhausted(self) -> None:
        def always_fail(batch):
            raise ValueError("Always fails")

        processor = BatchProcessor(
            batch_size=25, processor=always_fail,
        )
        result = processor.process_with_retry(self.items, max_retries=2)
        assert result.failed == 25
        assert len(result.errors) == 1
        assert result.errors[0]["attempts"] == 2

    def test_process_item_by_item(self) -> None:
        processor = BatchProcessor(batch_size=10)
        result = processor.process_item_by_item(
            self.items,
            item_processor=lambda item: {**item, "processed": True},
        )
        assert result.processed == 25
        assert all(item.get("processed") for item in result.output)

    def test_process_item_by_item_partial_failure(self) -> None:
        def sometimes_fail(item):
            if item["value"] == 5:
                raise ValueError("Item 5 fails")
            return {**item, "processed": True}

        processor = BatchProcessor(batch_size=10)
        result = processor.process_item_by_item(
            self.items,
            item_processor=sometimes_fail,
        )
        assert result.processed == 24
        assert result.failed == 1
        assert len(result.errors) == 1
        assert result.errors[0]["item_index"] == 5

    def test_batch_id_uniqueness(self) -> None:
        processor = BatchProcessor(batch_size=10)
        r1 = processor.process(self.items)
        r2 = processor.process(self.items)
        assert r1.batch_id != r2.batch_id

    def test_empty_items(self) -> None:
        processor = BatchProcessor(batch_size=10)
        result = processor.process([])
        assert result.total_items == 0
        assert result.processed == 0
        assert result.output == []

    def test_duration_tracking(self) -> None:
        processor = BatchProcessor(batch_size=10)
        result = processor.process(self.items)
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.duration_seconds >= 0


class TestModuleDocstringContract:
    def test_docstring_does_not_promise_parallel_execution(self) -> None:
        """Regression: module docstring must not over-promise capabilities.

        The module processes batches sequentially (a plain for-loop, no
        threading / concurrent.futures / multiprocessing), so its docstring
        must not claim to support 'parallel' execution (TICKET-329).
        """
        import personal_index.content_batch as cb

        doc = (cb.__doc__ or "").lower()
        assert "parallel" not in doc
