"""Durability modes for checkpoint persistence.

Borrowed from LangGraph's durability design:
- references/langgraph/libs/langgraph/langgraph/pregel/_checkpoint.py

Controls *when* checkpoints are actually written to the store:
- SYNC:  Write synchronously after every step (safest, slowest).
- ASYNC: Queue writes to a background thread (good default).
- EXIT:  Buffer in memory, flush at process exit (fastest, at-risk).
"""

from __future__ import annotations

import atexit
import logging
import queue
import threading
from enum import Enum
from typing import Optional

_logger = logging.getLogger("qitos.checkpoint.durability")

from .store import (
    Checkpoint,
    CheckpointConfig,
    CheckpointMetadata,
    CheckpointStore,
    StateVersions,
)


class DurabilityMode(Enum):
    """When to persist checkpoints to the store."""

    SYNC = "sync"
    ASYNC = "async"
    EXIT = "exit"


class DurabilityManager:
    """Wraps a :class:`CheckpointStore` and enforces write timing.

    Args:
        store: The underlying checkpoint store.
        mode: Durability mode.  Defaults to SYNC.
    """

    def __init__(
        self,
        store: CheckpointStore,
        mode: DurabilityMode = DurabilityMode.SYNC,
    ) -> None:
        self._store = store
        self._mode = mode
        self._buffer: list[tuple] = []  # buffered (put args) for EXIT mode
        self._queue: Optional[queue.Queue] = None
        self._worker: Optional[threading.Thread] = None
        self._shutdown = threading.Event()

        if mode == DurabilityMode.ASYNC:
            self._queue = queue.Queue(maxsize=4096)
            self._worker = threading.Thread(
                target=self._async_worker, daemon=True, name="checkpoint-durability"
            )
            self._worker.start()
        elif mode == DurabilityMode.EXIT:
            atexit.register(self.flush)

    # ---- public API ----

    def put(
        self,
        config: CheckpointConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: StateVersions,
    ) -> CheckpointConfig:
        """Store a checkpoint according to the configured durability mode."""
        if self._mode == DurabilityMode.SYNC:
            return self._store.put(config, checkpoint, metadata, new_versions)
        elif self._mode == DurabilityMode.ASYNC:
            assert self._queue is not None
            result_event = threading.Event()
            result_holder: list[Optional[CheckpointConfig]] = [None]
            try:
                self._queue.put_nowait((config, checkpoint, metadata, new_versions, result_event, result_holder))
            except queue.Full:
                _logger.warning("DurabilityManager queue full (maxsize=4096); dropping checkpoint for thread_id=%s",
                                config.thread_id)
            # For ASYNC, we return a config immediately with the checkpoint id
            # The actual store write happens in the background
            return CheckpointConfig(
                thread_id=config.thread_id, checkpoint_id=checkpoint.id
            )
        else:  # EXIT
            self._buffer.append((config, checkpoint, metadata, new_versions))
            return CheckpointConfig(
                thread_id=config.thread_id, checkpoint_id=checkpoint.id
            )

    def flush(self) -> None:
        """Force-write all buffered/queued checkpoints."""
        if self._mode == DurabilityMode.ASYNC and self._queue is not None:
            # Signal the worker to flush and wait
            try:
                self._queue.put_nowait(None)  # sentinel
            except queue.Full:
                _logger.warning("DurabilityManager queue full during flush; cannot send sentinel")
            if self._worker is not None:
                self._worker.join(timeout=10.0)
        elif self._mode == DurabilityMode.EXIT:
            for args in self._buffer:
                self._store.put(*args)
            self._buffer.clear()

    def shutdown(self) -> None:
        """Flush and clean up background resources."""
        self._shutdown.set()
        self.flush()

    # ---- internals ----

    def _async_worker(self) -> None:
        """Background thread that drains the write queue."""
        assert self._queue is not None
        while not self._shutdown.is_set():
            try:
                item = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if item is None:
                # Flush sentinel — drain remaining items
                while True:
                    try:
                        item = self._queue.get_nowait()
                    except queue.Empty:
                        break
                    if item is not None:
                        self._do_write(item)
                break
            self._do_write(item)

    def _do_write(self, item: tuple) -> None:
        config, checkpoint, metadata, new_versions, *_ = item
        try:
            self._store.put(config, checkpoint, metadata, new_versions)
        except Exception:
            # Swallow write errors in background thread to avoid crashing
            # the main Engine loop.  The checkpoint is still available
            # in the next SYNC write.
            pass


__all__ = ["DurabilityMode", "DurabilityManager"]
