"""Tests for checkpoint store ABC and core types."""

from qitos.checkpoint.store import (
    Checkpoint,
    CheckpointConfig,
    CheckpointId,
    CheckpointMetadata,
    CheckpointStore,
    CheckpointTuple,
    PendingWrite,
    StateVersions,
)
from qitos.checkpoint.versioning import StateVersionTracker
from qitos.checkpoint.durability import DurabilityMode, DurabilityManager
from qitos.checkpoint.pending_writes import PendingWriteManager
from qitos.checkpoint.memory_store import InMemoryCheckpointStore
from qitos.checkpoint.sqlite_store import SqliteCheckpointStore
from qitos.checkpoint.fork import fork_checkpoint, list_fork_history
import pytest


class TestCheckpointDataModel:
    """Test Checkpoint dataclass serialization."""

    def test_checkpoint_round_trip(self):
        cp = Checkpoint(
            id=CheckpointId("abc123"),
            thread_id="thread-1",
            step=5,
            state_data={"task": "hello", "current_step": 5},
            state_versions={"task": 1, "current_step": 3},
            versions_seen={"decide": {"task": 1}},
            pending_writes=[PendingWrite("t1", "findings", [1, 2, 3])],
            parent_id=CheckpointId("parent1"),
        )
        d = cp.to_dict()
        cp2 = Checkpoint.from_dict(d)
        assert cp2.id == "abc123"
        assert cp2.thread_id == "thread-1"
        assert cp2.step == 5
        assert cp2.state_data == {"task": "hello", "current_step": 5}
        assert cp2.state_versions == {"task": 1, "current_step": 3}
        assert cp2.versions_seen == {"decide": {"task": 1}}
        assert len(cp2.pending_writes) == 1
        assert cp2.pending_writes[0].task_id == "t1"
        assert cp2.pending_writes[0].value == [1, 2, 3]
        assert cp2.parent_id == "parent1"

    def test_checkpoint_defaults(self):
        cp = Checkpoint(
            id=CheckpointId("x"), thread_id="t", step=0, state_data={}
        )
        assert cp.state_versions == {}
        assert cp.versions_seen == {}
        assert cp.pending_writes == []
        assert cp.parent_id is None
        assert cp.schema_version == "v2"

    def test_checkpoint_config_equality(self):
        c1 = CheckpointConfig(thread_id="t1", checkpoint_id=CheckpointId("cp1"))
        c2 = CheckpointConfig(thread_id="t1", checkpoint_id=CheckpointId("cp1"))
        assert c1 == c2

    def test_checkpoint_config_latest(self):
        c = CheckpointConfig(thread_id="t1")
        assert c.checkpoint_id is None


class TestInMemoryCheckpointStore:
    """Test InMemoryCheckpointStore CRUD."""

    def test_put_and_get(self):
        store = InMemoryCheckpointStore()
        cp = Checkpoint(id=CheckpointId("cp1"), thread_id="t1", step=0, state_data={"x": 1})
        config = CheckpointConfig(thread_id="t1")
        meta: CheckpointMetadata = {"source": "loop", "step": 0}
        result_config = store.put(config, cp, meta, {})
        assert result_config.checkpoint_id == "cp1"
        assert result_config.thread_id == "t1"

        got = store.get(config)
        assert got is not None
        assert got.state_data == {"x": 1}

    def test_get_latest(self):
        store = InMemoryCheckpointStore()
        for i in range(3):
            cp = Checkpoint(
                id=CheckpointId(f"cp{i}"), thread_id="t1", step=i, state_data={"i": i}
            )
            store.put(CheckpointConfig(thread_id="t1"), cp, {"step": i}, {})

        # get without checkpoint_id returns latest
        latest = store.get(CheckpointConfig(thread_id="t1"))
        assert latest is not None
        assert latest.step == 2

    def test_list(self):
        store = InMemoryCheckpointStore()
        for i in range(5):
            cp = Checkpoint(
                id=CheckpointId(f"cp{i}"), thread_id="t1", step=i, state_data={"i": i}
            )
            store.put(CheckpointConfig(thread_id="t1"), cp, {"step": i}, {})

        items = list(store.list(CheckpointConfig(thread_id="t1"), limit=3))
        assert len(items) == 3
        # newest first
        assert items[0].checkpoint.step == 4

    def test_put_writes(self):
        store = InMemoryCheckpointStore()
        cp = Checkpoint(id=CheckpointId("cp1"), thread_id="t1", step=0, state_data={})
        config = CheckpointConfig(thread_id="t1")
        store.put(config, cp, {}, {})

        writes = [PendingWrite("task1", "findings", [1, 2])]
        store.put_writes(
            CheckpointConfig(thread_id="t1", checkpoint_id=CheckpointId("cp1")),
            writes,
            "task1",
        )

        tuple_ = store.get_tuple(CheckpointConfig(thread_id="t1"))
        assert tuple_ is not None
        assert tuple_.pending_writes is not None
        assert len(tuple_.pending_writes) == 1
        assert tuple_.pending_writes[0].value == [1, 2]

    def test_delete(self):
        store = InMemoryCheckpointStore()
        cp = Checkpoint(id=CheckpointId("cp1"), thread_id="t1", step=0, state_data={})
        store.put(CheckpointConfig(thread_id="t1"), cp, {}, {})
        store.delete(CheckpointConfig(thread_id="t1", checkpoint_id=CheckpointId("cp1")))
        assert store.get(CheckpointConfig(thread_id="t1")) is None

    def test_thread_isolation(self):
        store = InMemoryCheckpointStore()
        cp1 = Checkpoint(id=CheckpointId("cp1"), thread_id="t1", step=0, state_data={"x": 1})
        cp2 = Checkpoint(id=CheckpointId("cp2"), thread_id="t2", step=0, state_data={"x": 2})
        store.put(CheckpointConfig(thread_id="t1"), cp1, {}, {})
        store.put(CheckpointConfig(thread_id="t2"), cp2, {}, {})

        got1 = store.get(CheckpointConfig(thread_id="t1"))
        got2 = store.get(CheckpointConfig(thread_id="t2"))
        assert got1 is not None and got1.state_data["x"] == 1
        assert got2 is not None and got2.state_data["x"] == 2


class TestSqliteCheckpointStore:
    """Test SqliteCheckpointStore CRUD."""

    def test_put_and_get(self, tmp_path):
        store = SqliteCheckpointStore(str(tmp_path / "test.db"))
        cp = Checkpoint(id=CheckpointId("cp1"), thread_id="t1", step=0, state_data={"x": 1})
        config = CheckpointConfig(thread_id="t1")
        meta: CheckpointMetadata = {"source": "loop", "step": 0}
        store.put(config, cp, meta, {})

        got = store.get(config)
        assert got is not None
        assert got.state_data == {"x": 1}
        store.close()

    def test_multiple_checkpoints(self, tmp_path):
        store = SqliteCheckpointStore(str(tmp_path / "test.db"))
        for i in range(5):
            cp = Checkpoint(
                id=CheckpointId(f"cp{i}"), thread_id="t1", step=i, state_data={"i": i}
            )
            store.put(CheckpointConfig(thread_id="t1"), cp, {"step": i}, {})

        items = list(store.list(CheckpointConfig(thread_id="t1")))
        assert len(items) == 5
        # newest first
        assert items[0].checkpoint.step == 4
        store.close()

    def test_pending_writes(self, tmp_path):
        store = SqliteCheckpointStore(str(tmp_path / "test.db"))
        cp = Checkpoint(id=CheckpointId("cp1"), thread_id="t1", step=0, state_data={})
        store.put(CheckpointConfig(thread_id="t1"), cp, {}, {})

        writes = [PendingWrite("task1", "ch1", "val1")]
        store.put_writes(
            CheckpointConfig(thread_id="t1", checkpoint_id=CheckpointId("cp1")),
            writes,
            "task1",
        )

        tuple_ = store.get_tuple(CheckpointConfig(thread_id="t1"))
        assert tuple_ is not None
        assert tuple_.pending_writes is not None
        assert tuple_.pending_writes[0].value == "val1"
        store.close()

    def test_context_manager(self, tmp_path):
        with SqliteCheckpointStore(str(tmp_path / "test.db")) as store:
            cp = Checkpoint(id=CheckpointId("cp1"), thread_id="t1", step=0, state_data={})
            store.put(CheckpointConfig(thread_id="t1"), cp, {}, {})
            assert store.get(CheckpointConfig(thread_id="t1")) is not None

    def test_delete(self, tmp_path):
        store = SqliteCheckpointStore(str(tmp_path / "test.db"))
        cp = Checkpoint(id=CheckpointId("cp1"), thread_id="t1", step=0, state_data={})
        store.put(CheckpointConfig(thread_id="t1"), cp, {}, {})
        store.delete(CheckpointConfig(thread_id="t1", checkpoint_id=CheckpointId("cp1")))
        assert store.get(CheckpointConfig(thread_id="t1")) is None
        store.close()


class TestStateVersionTracker:
    """Test StateVersionTracker."""

    def test_bump(self):
        tracker = StateVersionTracker()
        assert tracker.bump("findings") == 1
        assert tracker.bump("findings") == 2
        assert tracker.get("findings") == 2
        assert tracker.get("unknown") == 0

    def test_bump_all(self):
        tracker = StateVersionTracker()
        new_versions = tracker.bump_all(["x", "y"])
        assert new_versions == {"x": 1, "y": 1}
        assert tracker.snapshot() == {"x": 1, "y": 1}

    def test_bump_from_diff(self):
        tracker = StateVersionTracker()
        before = {"a": 1, "b": 2}
        after = {"a": 1, "b": 3, "c": 4}
        new = tracker.bump_from_diff(before, after)
        assert "b" in new  # changed
        assert "c" in new  # added
        assert "a" not in new  # unchanged

    def test_snapshot_and_restore(self):
        tracker = StateVersionTracker()
        tracker.bump_all(["x", "y"])
        snap = tracker.snapshot()
        tracker2 = StateVersionTracker()
        tracker2.apply_versions(snap)
        assert tracker2.snapshot() == snap


class TestPendingWriteManager:
    """Test PendingWriteManager."""

    def test_begin_complete(self):
        store = InMemoryCheckpointStore()
        cp = Checkpoint(id=CheckpointId("cp1"), thread_id="t1", step=0, state_data={})
        config = CheckpointConfig(thread_id="t1")
        store.put(config, cp, {}, {})

        mgr = PendingWriteManager(store)
        mgr.begin_task("t1", "findings")
        mgr.complete_task("t1", [1, 2, 3], CheckpointConfig(thread_id="t1", checkpoint_id=CheckpointId("cp1")))
        assert mgr.get_pending("t1") == [1, 2, 3]

    def test_load_from_store(self):
        store = InMemoryCheckpointStore()
        cp = Checkpoint(id=CheckpointId("cp1"), thread_id="t1", step=0, state_data={})
        config = CheckpointConfig(thread_id="t1")
        store.put(config, cp, {}, {})
        store.put_writes(
            CheckpointConfig(thread_id="t1", checkpoint_id=CheckpointId("cp1")),
            [PendingWrite("t1", "ch", "val")],
            "t1",
        )

        mgr = PendingWriteManager(store)
        result = mgr.load_pending_from_store(
            CheckpointConfig(thread_id="t1", checkpoint_id=CheckpointId("cp1"))
        )
        assert result == {"t1": "val"}

    def test_reset(self):
        store = InMemoryCheckpointStore()
        mgr = PendingWriteManager(store)
        mgr.begin_task("t1", "ch")
        mgr.reset()
        assert mgr.get_pending("t1") is None


class TestDurabilityManager:
    """Test DurabilityManager modes."""

    def test_sync_mode(self):
        store = InMemoryCheckpointStore()
        dm = DurabilityManager(store, mode=DurabilityMode.SYNC)
        cp = Checkpoint(id=CheckpointId("cp1"), thread_id="t1", step=0, state_data={"x": 1})
        dm.put(CheckpointConfig(thread_id="t1"), cp, {}, {})
        # SYNC writes immediately
        assert store.get(CheckpointConfig(thread_id="t1")) is not None

    def test_exit_mode_flush(self):
        store = InMemoryCheckpointStore()
        dm = DurabilityManager(store, mode=DurabilityMode.EXIT)
        cp = Checkpoint(id=CheckpointId("cp1"), thread_id="t1", step=0, state_data={"x": 1})
        dm.put(CheckpointConfig(thread_id="t1"), cp, {}, {})
        # Not yet written
        # Now flush
        dm.flush()
        assert store.get(CheckpointConfig(thread_id="t1")) is not None


class TestFork:
    """Test fork and time-travel."""

    def test_fork_same_thread(self):
        store = InMemoryCheckpointStore()
        cp = Checkpoint(id=CheckpointId("cp1"), thread_id="t1", step=2, state_data={"x": 1})
        config = CheckpointConfig(thread_id="t1")
        store.put(config, cp, {"source": "loop", "step": 2}, {})

        forked_config = fork_checkpoint(store, CheckpointConfig(thread_id="t1"))
        assert forked_config.thread_id == "t1"
        assert forked_config.checkpoint_id is not None

        forked = store.get(forked_config)
        assert forked is not None
        assert forked.state_data == {"x": 1}
        assert forked.parent_id == CheckpointId("cp1")

    def test_fork_different_thread(self):
        store = InMemoryCheckpointStore()
        cp = Checkpoint(id=CheckpointId("cp1"), thread_id="t1", step=2, state_data={"x": 1})
        store.put(CheckpointConfig(thread_id="t1"), cp, {"step": 2}, {})

        forked_config = fork_checkpoint(
            store, CheckpointConfig(thread_id="t1"), new_thread_id="t2"
        )
        assert forked_config.thread_id == "t2"
        forked = store.get(forked_config)
        assert forked is not None
        assert forked.state_data == {"x": 1}

    def test_list_fork_history(self):
        store = InMemoryCheckpointStore()
        for i in range(3):
            cp = Checkpoint(
                id=CheckpointId(f"cp{i}"), thread_id="t1", step=i, state_data={"i": i}
            )
            store.put(CheckpointConfig(thread_id="t1"), cp, {"step": i}, {})

        history = list_fork_history(
            store, CheckpointConfig(thread_id="t1", checkpoint_id=CheckpointId("cp2"))
        )
        assert len(history) == 3
        assert history[0].checkpoint.step == 2
        assert history[2].checkpoint.step == 0
