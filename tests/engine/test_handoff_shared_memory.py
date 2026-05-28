"""Tests for v0.7 shared memory cross-agent wiring and HandoffContext.payload."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from qitos import AgentModule, AgentRegistry, AgentSpec, ContextStrategy, Decision, StateSchema
from qitos.core.agent_spec import HandoffContext
from qitos.core.shared_memory import (
    InMemorySharedMemory,
    SharedMemoryManager,
    SharedMemoryNamespace,
)
from qitos.engine.engine import Engine


# -- SharedMemoryManager cross-namespace tests --


class TestSharedMemoryManagerCrossAccess:
    def test_grant_read_access(self):
        mgr = SharedMemoryManager()
        mgr.namespace("agent_a")
        mgr.namespace("agent_b")
        mgr.grant_read_access("agent_b", "agent_a")
        assert "agent_a" in mgr.get_accessible_namespaces("agent_b")

    def test_get_accessible_namespaces_empty(self):
        mgr = SharedMemoryManager()
        assert mgr.get_accessible_namespaces("agent_a") == []

    def test_get_accessible_namespaces_multiple(self):
        mgr = SharedMemoryManager()
        mgr.grant_read_access("agent_c", "agent_a")
        mgr.grant_read_access("agent_c", "agent_b")
        accessible = mgr.get_accessible_namespaces("agent_c")
        assert "agent_a" in accessible
        assert "agent_b" in accessible

    def test_get_readonly_namespace_granted(self):
        mgr = SharedMemoryManager()
        # Agent A writes to its namespace
        ns_a = mgr.namespace("agent_a")
        ns_a.write("findings", ["bug1", "bug2"])
        # Grant B read access to A's namespace
        mgr.grant_read_access("agent_b", "agent_a")
        # B can get a read-only view
        ns_a_ro = mgr.get_readonly_namespace("agent_b", "agent_a")
        assert ns_a_ro is not None
        assert ns_a_ro.read_only is True
        assert ns_a_ro.read("findings") == ["bug1", "bug2"]

    def test_get_readonly_namespace_not_granted(self):
        mgr = SharedMemoryManager()
        mgr.namespace("agent_a")
        result = mgr.get_readonly_namespace("agent_b", "agent_a")
        assert result is None

    def test_readonly_namespace_cannot_write(self):
        mgr = SharedMemoryManager()
        mgr.namespace("agent_a")
        mgr.grant_read_access("agent_b", "agent_a")
        ns_a_ro = mgr.get_readonly_namespace("agent_b", "agent_a")
        with pytest.raises(PermissionError):
            ns_a_ro.write("key", "value")

    def test_clear_all_clears_grants(self):
        mgr = SharedMemoryManager()
        mgr.grant_read_access("agent_b", "agent_a")
        mgr.clear_all()
        assert mgr.get_accessible_namespaces("agent_b") == []


# -- HandoffContext.payload consumption tests --


@dataclass
class PayloadState(StateSchema):
    scratchpad: list[str] = field(default_factory=list)


class PayloadOrchestrator(AgentModule[PayloadState, Any, Any]):
    """Orchestrator that hands off with payload."""

    name = "payload_orchestrator"

    def init_state(self, task, **kwargs):
        return PayloadState(task=task, max_steps=8)

    def decide(self, state, observation):
        if state.current_step == 0:
            return Decision.handoff(target="worker", rationale="Delegate")
        return None

    def reduce(self, state, observation, decision):
        return state


class PayloadWorker(AgentModule[PayloadState, Any, Any]):
    """Worker that can read handoff payload from shared memory."""

    name = "payload_worker"

    def init_state(self, task, **kwargs):
        return PayloadState(task=task, max_steps=8)

    def decide(self, state, observation):
        return Decision.final(answer="Done")

    def reduce(self, state, observation, decision):
        if decision.mode == "final":
            state.final_result = str(decision.final_answer or "")
        return state


class TestHandoffContextPayloadConsumption:
    def test_payload_written_to_shared_memory(self):
        """HandoffContext.payload entries are written to target agent's shared memory."""
        from qitos.core.shared_memory import InMemorySharedMemory
        from unittest.mock import MagicMock

        llm = MagicMock()
        shared_mem = InMemorySharedMemory()
        mgr = SharedMemoryManager(memory=shared_mem)

        orchestrator = PayloadOrchestrator(llm=llm)
        worker = PayloadWorker(llm=llm)

        registry = AgentRegistry()
        registry.register(AgentSpec(
            name="worker",
            description="Worker",
            agent=worker,
            handoff_context=HandoffContext(
                strategy=ContextStrategy.SUMMARY,
                payload={"task_type": "code_fix", "priority": "high"},
            ),
            shared_memory=shared_mem,
        ))

        engine = Engine(
            agent=orchestrator,
            agent_registry=registry,
            auto_approve=True,
        )
        # Manually set shared memory manager
        engine._shared_memory_manager = mgr

        result = engine.run("Test task", max_steps=5)

        # The payload should be written to the worker's namespace
        worker_ns = mgr.namespace("worker")
        assert worker_ns.read("handoff_payload:task_type") == "code_fix"
        assert worker_ns.read("handoff_payload:priority") == "high"

    def test_payload_empty_no_write(self):
        """Empty payload does not write to shared memory."""
        from unittest.mock import MagicMock

        llm = MagicMock()
        shared_mem = InMemorySharedMemory()
        mgr = SharedMemoryManager(memory=shared_mem)

        orchestrator = PayloadOrchestrator(llm=llm)
        worker = PayloadWorker(llm=llm)

        registry = AgentRegistry()
        registry.register(AgentSpec(
            name="worker",
            description="Worker",
            agent=worker,
            handoff_context=HandoffContext(
                strategy=ContextStrategy.SUMMARY,
                payload={},
            ),
        ))

        engine = Engine(
            agent=orchestrator,
            agent_registry=registry,
            auto_approve=True,
        )
        engine._shared_memory_manager = mgr

        result = engine.run("Test task", max_steps=5)

        # No payload entries should exist
        worker_ns = mgr.namespace("worker")
        assert worker_ns.list_keys() == [] or all(
            not k.startswith("handoff_payload:") for k in worker_ns.list_keys()
        )


class TestCrossNamespaceReadAccess:
    def test_worker_gets_read_access_to_orchestrator_namespace(self):
        """After handoff with shared_memory set, worker can read orchestrator's namespace."""
        from unittest.mock import MagicMock

        llm = MagicMock()
        shared_mem = InMemorySharedMemory()
        mgr = SharedMemoryManager(memory=shared_mem)

        # Orchestrator writes to its namespace before handoff
        orch_ns = mgr.namespace("payload_orchestrator")
        orch_ns.write("findings", ["item1", "item2"])

        orchestrator = PayloadOrchestrator(llm=llm)
        worker = PayloadWorker(llm=llm)

        registry = AgentRegistry()
        registry.register(AgentSpec(
            name="worker",
            description="Worker",
            agent=worker,
            shared_memory=shared_mem,
        ))

        engine = Engine(
            agent=orchestrator,
            agent_registry=registry,
            auto_approve=True,
        )
        engine._shared_memory_manager = mgr

        result = engine.run("Test task", max_steps=5)

        # Worker should have been granted read access to orchestrator's namespace
        accessible = mgr.get_accessible_namespaces("worker")
        assert "payload_orchestrator" in accessible

        # Worker can get a read-only view
        orch_ro = mgr.get_readonly_namespace("worker", "payload_orchestrator")
        assert orch_ro is not None
        assert orch_ro.read_only is True
        assert orch_ro.read("findings") == ["item1", "item2"]

    def test_no_cross_access_without_shared_memory(self):
        """Without shared_memory set, no cross-namespace read access is granted."""
        from unittest.mock import MagicMock

        llm = MagicMock()
        shared_mem = InMemorySharedMemory()
        mgr = SharedMemoryManager(memory=shared_mem)

        orchestrator = PayloadOrchestrator(llm=llm)
        worker = PayloadWorker(llm=llm)

        registry = AgentRegistry()
        registry.register(AgentSpec(
            name="worker",
            description="Worker",
            agent=worker,
            # No shared_memory set
        ))

        engine = Engine(
            agent=orchestrator,
            agent_registry=registry,
            auto_approve=True,
        )
        engine._shared_memory_manager = mgr

        result = engine.run("Test task", max_steps=5)

        # Worker should NOT have read access
        accessible = mgr.get_accessible_namespaces("worker")
        assert "payload_orchestrator" not in accessible
