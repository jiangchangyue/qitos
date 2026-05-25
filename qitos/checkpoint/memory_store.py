"""In-memory checkpoint store for development and testing.

Dict-backed implementation of :class:`CheckpointStore`.
"""

from __future__ import annotations

import threading
from typing import Dict, Iterator, List, Optional, Sequence
from uuid import uuid4

from .store import (
    Checkpoint,
    CheckpointConfig,
    CheckpointId,
    CheckpointMetadata,
    CheckpointStore,
    CheckpointTuple,
    PendingWrite,
    StateVersions,
)


class InMemoryCheckpointStore(CheckpointStore):
    """Thread-safe, dict-backed checkpoint store.

    Suitable for development, testing, and single-process scenarios.
    All data is lost when the process exits.
    """

    def __init__(self) -> None:
        self._store: Dict[CheckpointId, CheckpointTuple] = {}
        self._thread_index: Dict[str, List[CheckpointId]] = {}
        self._lock = threading.Lock()

    # ---- helpers ----

    def _latest_id(self, thread_id: str) -> Optional[CheckpointId]:
        ids = self._thread_index.get(thread_id)
        if not ids:
            return None
        return ids[-1]

    def _resolve_id(self, config: CheckpointConfig) -> Optional[CheckpointId]:
        if config.checkpoint_id is not None:
            return config.checkpoint_id
        return self._latest_id(config.thread_id)

    # ---- sync interface ----

    def put(
        self,
        config: CheckpointConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: StateVersions,
    ) -> CheckpointConfig:
        with self._lock:
            parent_id = self._latest_id(config.thread_id)
            # determine parent_config
            parent_config: Optional[CheckpointConfig] = None
            if parent_id is not None:
                parent_config = CheckpointConfig(
                    thread_id=config.thread_id, checkpoint_id=parent_id
                )

            tuple_ = CheckpointTuple(
                config=config,
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config=parent_config,
                pending_writes=None,
            )
            self._store[checkpoint.id] = tuple_

            tid = config.thread_id
            if tid not in self._thread_index:
                self._thread_index[tid] = []
            self._thread_index[tid].append(checkpoint.id)

            return CheckpointConfig(
                thread_id=config.thread_id, checkpoint_id=checkpoint.id
            )

    def get_tuple(self, config: CheckpointConfig) -> Optional[CheckpointTuple]:
        with self._lock:
            cp_id = self._resolve_id(config)
            if cp_id is None:
                return None
            return self._store.get(cp_id)

    def list(
        self,
        config: CheckpointConfig,
        *,
        limit: Optional[int] = None,
        before: Optional[CheckpointConfig] = None,
    ) -> Iterator[CheckpointTuple]:
        with self._lock:
            ids = list(self._thread_index.get(config.thread_id, []))

        # newest first
        ids = list(reversed(ids))

        if before is not None and before.checkpoint_id is not None:
            try:
                idx = ids.index(before.checkpoint_id)
                ids = ids[idx + 1 :]
            except ValueError:
                pass

        if limit is not None:
            ids = ids[:limit]

        for cp_id in ids:
            entry = self._store.get(cp_id)
            if entry is not None:
                yield entry

    def put_writes(
        self,
        config: CheckpointConfig,
        writes: Sequence[PendingWrite],
        task_id: str,
    ) -> None:
        with self._lock:
            cp_id = self._resolve_id(config)
            if cp_id is None:
                return
            existing = self._store.get(cp_id)
            if existing is None:
                return
            current_writes = list(existing.pending_writes or [])
            current_writes.extend(writes)
            self._store[cp_id] = CheckpointTuple(
                config=existing.config,
                checkpoint=existing.checkpoint,
                metadata=existing.metadata,
                parent_config=existing.parent_config,
                pending_writes=current_writes,
            )

    def delete(self, config: CheckpointConfig) -> None:
        with self._lock:
            cp_id = self._resolve_id(config)
            if cp_id is None:
                return
            self._store.pop(cp_id, None)
            ids = self._thread_index.get(config.thread_id, [])
            if cp_id in ids:
                ids.remove(cp_id)


__all__ = ["InMemoryCheckpointStore"]
