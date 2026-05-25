"""QitOS Checkpoint — run persistence and resume support.

Exports both the new v2 API (CheckpointStore, Checkpoint, etc.) and the
legacy v1 API (CheckpointData, CheckpointManager) for backward compatibility.
"""

from .checkpoint import CheckpointData, CheckpointManager
from .durability import DurabilityManager, DurabilityMode
from .fork import fork_checkpoint, list_fork_history
from .memory_store import InMemoryCheckpointStore
from .pending_writes import PendingWriteManager
from .sqlite_store import SqliteCheckpointStore
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
from .versioning import StateVersionTracker

__all__ = [
    # v2 API
    "CheckpointStore",
    "Checkpoint",
    "CheckpointConfig",
    "CheckpointId",
    "CheckpointMetadata",
    "CheckpointTuple",
    "PendingWrite",
    "StateVersions",
    "InMemoryCheckpointStore",
    "SqliteCheckpointStore",
    "StateVersionTracker",
    "PendingWriteManager",
    "DurabilityManager",
    "DurabilityMode",
    "fork_checkpoint",
    "list_fork_history",
    # v1 legacy (deprecated)
    "CheckpointData",
    "CheckpointManager",
]
