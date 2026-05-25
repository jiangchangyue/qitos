"""Pending write manager for crash-recovery of partial tool results.

Borrowed from LangGraph's put_writes mechanism:
- references/langgraph/libs/langgraph/langgraph/pregel/_loop.py

ActionExecutor calls ``begin_task()`` before tool execution and
``complete_task()`` after.  On crash, the manager's persisted writes
allow resuming with partial results already committed to the store.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .store import CheckpointConfig, CheckpointId, CheckpointStore, PendingWrite


class PendingWriteManager:
    """Manages partial tool-execution results for a single Engine run.

    Works in conjunction with a :class:`CheckpointStore` to persist
    intermediate writes so that a crashed run can be resumed without
    re-executing already-completed tools.
    """

    def __init__(self, store: CheckpointStore) -> None:
        self._store = store
        self._tasks: Dict[str, PendingWrite] = {}

    # ---- lifecycle ----

    def begin_task(self, task_id: str, channel: str) -> None:
        """Mark a tool execution as started (in-memory only)."""
        self._tasks[task_id] = PendingWrite(task_id=task_id, channel=channel, value=None)

    def complete_task(self, task_id: str, value: Any, config: CheckpointConfig) -> None:
        """Record a completed tool result and persist it.

        Args:
            task_id: Unique identifier for the tool execution.
            value: The tool result.
            config: Checkpoint config to associate the write with.
        """
        write = PendingWrite(task_id=task_id, channel=self._tasks[task_id].channel, value=value)
        self._tasks[task_id] = write
        self._store.put_writes(config, [write], task_id=task_id)

    def get_pending(self, task_id: str) -> Optional[Any]:
        """Retrieve a pending result by task_id (from in-memory buffer)."""
        write = self._tasks.get(task_id)
        return write.value if write else None

    def load_pending_from_store(self, config: CheckpointConfig) -> Dict[str, Any]:
        """Load persisted pending writes from the store.

        Called during resume to recover results from a crashed run.
        Returns a dict of task_id -> value.
        """
        result: Dict[str, Any] = {}
        tuple_ = self._store.get_tuple(config)
        if tuple_ is None or tuple_.pending_writes is None:
            return result
        for w in tuple_.pending_writes:
            result[w.task_id] = w.value
            self._tasks[w.task_id] = w
        return result

    def commit_writes(self, config: CheckpointConfig) -> None:
        """Flush all buffered writes to the store.

        Called at the end of a step to ensure all writes are persisted
        before the checkpoint is saved.
        """
        writes = [w for w in self._tasks.values() if w.value is not None]
        if not writes:
            return
        for w in writes:
            self._store.put_writes(config, [w], task_id=w.task_id)

    def clear_task(self, task_id: str) -> None:
        """Remove a completed/errored task from the buffer."""
        self._tasks.pop(task_id, None)

    def reset(self) -> None:
        """Clear all in-memory state for a new run."""
        self._tasks.clear()


__all__ = ["PendingWriteManager"]
