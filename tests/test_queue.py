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
