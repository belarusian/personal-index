# TICKET-336: queue.TaskQueue.completed_count docstring over-promises "completed"

Status: OPEN
Module: personal_index/queue.py
Class: (b) docstring over-promises behavior the code does not do

## Symptom
`TaskQueue.completed_count` property docstring reads:
    """Number of completed tasks retained."""
The body returns `len(self._completed)`. But `self._completed` is appended to
by BOTH `complete_task` (queue.py:179) AND `fail_task` (queue.py:197). So the
count includes FAILED tasks, not only completed ones. The docstring therefore
over-promises: it claims "completed tasks" when the value also counts failed
tasks retained in the same list.

## Evidence
personal_index/queue.py:91   (self._completed: list[Task] = [])
personal_index/queue.py:179  (complete_task: self._completed.append(task))
personal_index/queue.py:197  (fail_task: self._completed.append(task))
personal_index/queue.py:222-224 (completed_count returns len(self._completed))

## Minimal additive fix
Reword the `completed_count` docstring to what the code actually does:
    """Number of finished (completed or failed) tasks retained."""
Do NOT change which tasks are appended to self._completed (behavior change,
out of scope).

## Regression test
Assert via inspect.getsource that the completed_count docstring no longer
claims "completed tasks" alone, and that completed_count counts a failed task
as well as a completed one (behavior unchanged).

Issue: #510
