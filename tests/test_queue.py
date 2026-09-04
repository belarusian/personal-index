"""Tests for the priority task queue."""

from personal_index.queue import Task, TaskPriority, TaskQueue, TaskStatus


class TestTask:
    def test_creation(self):
        task = Task(priority=TaskPriority.NORMAL.value, sequence=0, task_id="t1")
        assert task.status == TaskStatus.PENDING
        assert task.duration is None

    def test_start(self):
        task = Task(priority=0, sequence=0, task_id="t1")
        task.start()
        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None

    def test_complete(self):
        task = Task(priority=0, sequence=0, task_id="t1")
        task.start()
        task.complete(result="done")
        assert task.status == TaskStatus.COMPLETED
        assert task.result == "done"
        assert task.duration is not None

    def test_fail(self):
        task = Task(priority=0, sequence=0, task_id="t1")
        task.fail("error msg")
        assert task.status == TaskStatus.FAILED
        assert task.error == "error msg"

    def test_cancel(self):
        task = Task(priority=0, sequence=0, task_id="t1")
        task.cancel()
        assert task.status == TaskStatus.CANCELLED


class TestTaskQueue:
    def test_enqueue_dequeue(self):
        q = TaskQueue()
        q.enqueue("t1", "test task")
        assert q.size == 1
        result = q.dequeue()
        assert result is not None
        assert result.task_id == "t1"
        assert result.status == TaskStatus.RUNNING

    def test_priority_ordering(self):
        q = TaskQueue()
        q.enqueue("low", priority=TaskPriority.LOW)
        q.enqueue("high", priority=TaskPriority.HIGH)
        q.enqueue("critical", priority=TaskPriority.CRITICAL)
        first = q.dequeue()
        assert first.task_id == "critical"

    def test_max_size_eviction(self):
        q = TaskQueue(max_size=3)
        q.enqueue("a", priority=TaskPriority.NORMAL)
        q.enqueue("b", priority=TaskPriority.NORMAL)
        q.enqueue("c", priority=TaskPriority.NORMAL)
        q.enqueue("d", priority=TaskPriority.NORMAL)
        assert q.size <= 3

    def test_get_task(self):
        q = TaskQueue()
        q.enqueue("t1", "test")
        task = q.get_task("t1")
        assert task is not None
        assert task.name == "test"

    def test_get_missing_task(self):
        q = TaskQueue()
        assert q.get_task("missing") is None

    def test_cancel_task(self):
        q = TaskQueue()
        q.enqueue("t1")
        assert q.cancel_task("t1") is True
        task = q.get_task("t1")
        assert task.status == TaskStatus.CANCELLED

    def test_complete_task(self):
        q = TaskQueue()
        q.enqueue("t1")
        q.dequeue()
        assert q.complete_task("t1", result="ok") is True
        assert q.completed_count == 1

    def test_fail_task(self):
        q = TaskQueue()
        q.enqueue("t1")
        q.dequeue()
        assert q.fail_task("t1", "oops") is True
        task = q.get_task("t1")
        assert task.error == "oops"

    def test_completed_count_counts_failed_tasks(self):
        q = TaskQueue()
        q.enqueue("t1")
        q.dequeue()
        assert q.fail_task("t1", "oops") is True
        assert q.completed_count == 1

    def test_completed_count_docstring_not_overpromise(self):
        import inspect
        src = inspect.getsource(TaskQueue.completed_count.fget)
        assert "Number of completed tasks retained" not in src
        assert "completed or failed" in src

    def test_pending_count(self):
        q = TaskQueue()
        q.enqueue("t1")
        q.enqueue("t2")
        assert q.pending_count == 2
        q.dequeue()
        assert q.pending_count == 1

    def test_stats(self):
        q = TaskQueue()
        q.enqueue("t1")
        stats = q.get_stats()
        assert stats["queue_size"] == 1
        assert stats["total_tasks"] == 1

    def test_clear_completed(self):
        q = TaskQueue()
        for i in range(10):
            q.enqueue(f"t{i}")
            q.dequeue()
            q.complete_task(f"t{i}")
        assert q.completed_count == 10
        q.clear_completed(keep=5)
        assert q.completed_count == 5

    def test_empty_dequeue(self):
        q = TaskQueue()
        assert q.dequeue() is None

    def test_data_passthrough(self):
        q = TaskQueue()
        q.enqueue("t1", data={"url": "http://example.com"})
        task = q.get_task("t1")
        assert task.data["url"] == "http://example.com"

    def test_cancel_running_task_fails(self):
        q = TaskQueue()
        q.enqueue("t1")
        q.dequeue()
        assert q.cancel_task("t1") is False

    def test_cancel_nonexistent_task(self):
        q = TaskQueue()
        assert q.cancel_task("nope") is False

    def test_complete_pending_task_fails(self):
        q = TaskQueue()
        q.enqueue("t1")
        assert q.complete_task("t1") is False

    def test_complete_nonexistent_task(self):
        q = TaskQueue()
        assert q.complete_task("nope") is False

    def test_fail_pending_task_fails(self):
        q = TaskQueue()
        q.enqueue("t1")
        assert q.fail_task("t1", "err") is False

    def test_fail_nonexistent_task(self):
        q = TaskQueue()
        assert q.fail_task("nope", "err") is False

    def test_dequeue_skips_cancelled(self):
        q = TaskQueue()
        q.enqueue("t1")
        q.cancel_task("t1")
        q.enqueue("t2")
        result = q.dequeue()
        assert result is not None
        assert result.task_id == "t2"

    def test_stats_multiple_statuses(self):
        q = TaskQueue()
        q.enqueue("t1")
        q.enqueue("t2")
        dequeued = q.dequeue()
        q.complete_task(dequeued.task_id)
        q.enqueue("t3")
        q.cancel_task("t3")
        stats = q.get_stats()
        assert stats["status_breakdown"]["pending"] == 1
        assert stats["status_breakdown"]["completed"] == 1
        assert stats["status_breakdown"]["cancelled"] == 1

    def test_clear_completed_keep_zero(self):
        q = TaskQueue()
        q.enqueue("t1")
        q.dequeue()
        q.complete_task("t1")
        q.clear_completed(keep=0)
        assert q.completed_count == 1

    def test_clear_completed_nothing_to_clear(self):
        q = TaskQueue()
        q.clear_completed(keep=5)
        assert q.completed_count == 0

    def test_fifo_same_priority(self):
        q = TaskQueue()
        q.enqueue("first", priority=TaskPriority.NORMAL)
        q.enqueue("second", priority=TaskPriority.NORMAL)
        q.enqueue("third", priority=TaskPriority.NORMAL)
        assert q.dequeue().task_id == "first"
        assert q.dequeue().task_id == "second"
        assert q.dequeue().task_id == "third"

    def test_enqueue_duplicate_task_id(self):
        q = TaskQueue()
        q.enqueue("t1", name="first")
        q.enqueue("t1", name="second")
        task = q.get_task("t1")
        assert task.name == "second"

    def test_all_priority_levels(self):
        q = TaskQueue()
        q.enqueue("bg", priority=TaskPriority.BACKGROUND)
        q.enqueue("low", priority=TaskPriority.LOW)
        q.enqueue("norm", priority=TaskPriority.NORMAL)
        q.enqueue("high", priority=TaskPriority.HIGH)
        q.enqueue("crit", priority=TaskPriority.CRITICAL)
        order = []
        while True:
            t = q.dequeue()
            if t is None:
                break
            order.append(t.task_id)
        assert order == ["crit", "high", "norm", "low", "bg"]

    def test_eviction_removes_heap_top_on_full(self):
        q = TaskQueue(max_size=2)
        q.enqueue("high", priority=TaskPriority.HIGH)
        q.enqueue("low", priority=TaskPriority.LOW)
        q.enqueue("critical", priority=TaskPriority.CRITICAL)
        evicted = q.get_task("high")
        assert evicted is None or evicted.status == TaskStatus.CANCELLED

    def test_task_duration_not_started(self):
        task = Task(priority=0, sequence=0, task_id="t1")
        assert task.duration is None

    def test_task_duration_started_not_completed(self):
        task = Task(priority=0, sequence=0, task_id="t1")
        task.start()
        assert task.duration is None

    def test_task_status_transitions_complete(self):
        task = Task(priority=0, sequence=0, task_id="t1")
        assert task.status == TaskStatus.PENDING
        task.start()
        assert task.status == TaskStatus.RUNNING
        task.complete()
        assert task.status == TaskStatus.COMPLETED

    def test_task_status_transitions_fail(self):
        task = Task(priority=0, sequence=0, task_id="t1")
        task.start()
        task.fail("boom")
        assert task.status == TaskStatus.FAILED
        assert task.error == "boom"

    def test_empty_queue_stats(self):
        q = TaskQueue()
        stats = q.get_stats()
        assert stats["queue_size"] == 0
        assert stats["total_tasks"] == 0
        assert stats["completed"] == 0
        assert stats["status_breakdown"] == {}
