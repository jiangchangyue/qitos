"""Tests for SharedMemoryNamespace and SharedMemoryManager."""

from __future__ import annotations

import pytest

from qitos.core.shared_memory import (
    InMemorySharedMemory,
    FileSharedMemory,
    SharedMemoryNamespace,
    SharedMemoryManager,
)


# ---------------------------------------------------------------------------
# SharedMemoryNamespace
# ---------------------------------------------------------------------------


class TestSharedMemoryNamespace:
    def test_write_and_read(self):
        mem = InMemorySharedMemory()
        ns = SharedMemoryNamespace(mem, "agent_a")
        ns.write("key1", "value1")
        assert ns.read("key1") == "value1"

    def test_keys_are_prefixed(self):
        mem = InMemorySharedMemory()
        ns = SharedMemoryNamespace(mem, "agent_a")
        ns.write("key1", "value1")
        # Underlying key should be prefixed
        assert mem.read("agent_a:key1") == "value1"

    def test_list_keys_strips_prefix(self):
        mem = InMemorySharedMemory()
        ns = SharedMemoryNamespace(mem, "agent_a")
        ns.write("x", 1)
        ns.write("y", 2)
        assert set(ns.list_keys()) == {"x", "y"}

    def test_delete(self):
        mem = InMemorySharedMemory()
        ns = SharedMemoryNamespace(mem, "agent_a")
        ns.write("key1", "value1")
        assert ns.delete("key1") is True
        assert ns.read("key1") is None

    def test_delete_nonexistent(self):
        mem = InMemorySharedMemory()
        ns = SharedMemoryNamespace(mem, "agent_a")
        assert ns.delete("nope") is False

    def test_clear(self):
        mem = InMemorySharedMemory()
        ns = SharedMemoryNamespace(mem, "agent_a")
        ns.write("a", 1)
        ns.write("b", 2)
        ns.clear()
        assert ns.list_keys() == []

    def test_namespace_isolation(self):
        mem = InMemorySharedMemory()
        ns_a = SharedMemoryNamespace(mem, "agent_a")
        ns_b = SharedMemoryNamespace(mem, "agent_b")
        ns_a.write("key", "from_a")
        ns_b.write("key", "from_b")
        assert ns_a.read("key") == "from_a"
        assert ns_b.read("key") == "from_b"

    def test_read_only_prevents_write(self):
        mem = InMemorySharedMemory()
        ns = SharedMemoryNamespace(mem, "agent_a", read_only=True)
        with pytest.raises(PermissionError, match="read-only"):
            ns.write("key", "value")

    def test_read_only_prevents_delete(self):
        mem = InMemorySharedMemory()
        # Write via writable namespace
        ns_w = SharedMemoryNamespace(mem, "agent_a", read_only=False)
        ns_w.write("key", "value")
        # Read via read-only namespace
        ns_r = SharedMemoryNamespace(mem, "agent_a", read_only=True)
        assert ns_r.read("key") == "value"
        with pytest.raises(PermissionError, match="read-only"):
            ns_r.delete("key")

    def test_read_only_prevents_clear(self):
        mem = InMemorySharedMemory()
        ns = SharedMemoryNamespace(mem, "agent_a", read_only=True)
        with pytest.raises(PermissionError, match="read-only"):
            ns.clear()

    def test_read_only_allows_read(self):
        mem = InMemorySharedMemory()
        ns_w = SharedMemoryNamespace(mem, "agent_a")
        ns_w.write("key", "value")
        ns_r = SharedMemoryNamespace(mem, "agent_a", read_only=True)
        assert ns_r.read("key") == "value"

    def test_read_only_list_keys(self):
        mem = InMemorySharedMemory()
        ns_w = SharedMemoryNamespace(mem, "agent_a")
        ns_w.write("a", 1)
        ns_r = SharedMemoryNamespace(mem, "agent_a", read_only=True)
        assert ns_r.list_keys() == ["a"]

    def test_namespace_property(self):
        mem = InMemorySharedMemory()
        ns = SharedMemoryNamespace(mem, "test_ns")
        assert ns.namespace == "test_ns"

    def test_read_only_property(self):
        mem = InMemorySharedMemory()
        ns = SharedMemoryNamespace(mem, "test_ns", read_only=True)
        assert ns.read_only is True
        ns2 = SharedMemoryNamespace(mem, "test_ns2", read_only=False)
        assert ns2.read_only is False


# ---------------------------------------------------------------------------
# SharedMemoryManager
# ---------------------------------------------------------------------------


class TestSharedMemoryManager:
    def test_default_in_memory(self):
        mgr = SharedMemoryManager()
        assert isinstance(mgr.memory, InMemorySharedMemory)

    def test_custom_backing_store(self):
        mem = InMemorySharedMemory()
        mgr = SharedMemoryManager(memory=mem)
        assert mgr.memory is mem

    def test_namespace_creation(self):
        mgr = SharedMemoryManager()
        ns = mgr.namespace("agent_a")
        assert isinstance(ns, SharedMemoryNamespace)
        assert ns.namespace == "agent_a"

    def test_namespace_reuse(self):
        mgr = SharedMemoryManager()
        ns1 = mgr.namespace("agent_a")
        ns2 = mgr.namespace("agent_a")
        assert ns1 is ns2

    def test_namespace_read_only(self):
        mgr = SharedMemoryManager()
        ns = mgr.namespace("agent_a", read_only=True)
        assert ns.read_only is True

    def test_list_namespaces(self):
        mgr = SharedMemoryManager()
        mgr.namespace("a")
        mgr.namespace("b")
        assert set(mgr.list_namespaces()) == {"a", "b"}

    def test_global_namespace(self):
        mgr = SharedMemoryManager()
        ns = mgr.global_namespace()
        assert ns.namespace == "__global__"
        assert ns.read_only is False

    def test_cross_namespace_sharing(self):
        mgr = SharedMemoryManager()
        ns_a = mgr.namespace("agent_a")
        ns_global = mgr.global_namespace()
        ns_global.write("shared_data", {"result": 42})
        # agent_a can't see global keys via its namespace
        assert ns_a.read("shared_data") is None
        # But global ns can read it
        assert ns_global.read("shared_data") == {"result": 42}

    def test_clear_all(self):
        mgr = SharedMemoryManager()
        ns_a = mgr.namespace("a")
        ns_g = mgr.global_namespace()
        ns_a.write("key", "val")
        ns_g.write("gkey", "gval")
        mgr.clear_all()
        # Data is cleared
        assert ns_a.list_keys() == []
        assert ns_g.list_keys() == []
        # Namespace cache is cleared
        assert mgr.list_namespaces() == []

    def test_read_only_view_for_sub_agent(self):
        """Simulate handoff: parent writes, sub-agent gets read-only view."""
        mgr = SharedMemoryManager()
        parent = mgr.namespace("parent")
        parent.write("task", "analyze")
        parent.write("context", {"files": ["a.py"]})

        # Sub-agent gets read-only view of parent's namespace
        child_view = mgr.namespace("parent", read_only=True)
        assert child_view.read("task") == "analyze"
        with pytest.raises(PermissionError):
            child_view.write("task", "modified")

    def test_with_file_backed_memory(self, tmp_path):
        path = tmp_path / "shared.json"
        mem = FileSharedMemory(path)
        mgr = SharedMemoryManager(memory=mem)
        ns = mgr.namespace("agent_a")
        ns.write("key", "value")
        assert ns.read("key") == "value"
