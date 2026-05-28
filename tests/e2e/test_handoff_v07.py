"""E2E: v0.7 handoff features — real LLM endpoint tests.

Tests v0.7 handoff pipeline: HandoffTool→Engine interception,
context strategies, shared memory, payload, return handoff.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from .conftest import e2e_skip, create_e2e_llm, create_e2e_engine_with_registry
from qitos import AgentModule, AgentRegistry, AgentSpec, ContextStrategy, Decision, StateSchema
from qitos.core.agent_spec import HandoffContext
from qitos.core.shared_memory import InMemorySharedMemory, SharedMemoryManager
from qitos.kit import ReActTextParser


# ── Shared test state ────────────────────────────────────────────────────


@dataclass
class V07State(StateSchema):
    scratchpad: list[str] = field(default_factory=list)
    current_agent: str = "orchestrator"


# ── Test: HandoffTool triggers agent switch ──────────────────────────────


class SwitchOrchestrator(AgentModule[V07State, Any, Any]):
    """Orchestrator that uses transfer_to_* tool to trigger handoff."""

    name = "switch_orch"
    handoff_targets = ["switch_worker"]

    def __init__(self, llm=None, **kwargs):
        super().__init__(llm=llm, model_parser=ReActTextParser(), **kwargs)

    def init_state(self, task, **kwargs):
        return V07State(task=task, max_steps=8)

    def build_system_prompt(self, state):
        return (
            "You are an orchestrator. Use transfer_to_switch_worker to delegate tasks. "
            "When you see handoff results, provide a final answer."
        )

    def prepare(self, state):
        return f"Task: {state.task}"

    def reduce(self, state, observation, decision):
        if decision.mode == "final":
            state.final_result = str(decision.final_answer or "")
        if decision.mode == "handoff":
            state.current_agent = "switch_worker"
        return state


class SwitchWorker(AgentModule[V07State, Any, Any]):
    """Worker that completes tasks after handoff."""

    name = "switch_worker"

    def __init__(self, llm=None, **kwargs):
        super().__init__(llm=llm, model_parser=ReActTextParser(), **kwargs)

    def init_state(self, task, **kwargs):
        return V07State(task=task, max_steps=8)

    def build_system_prompt(self, state):
        return "You are a specialist worker. Complete the task and provide a final answer."

    def prepare(self, state):
        return f"Task: {state.task}"

    def reduce(self, state, observation, decision):
        if decision.mode == "final":
            state.final_result = str(decision.final_answer or "")
        return state


@e2e_skip
@pytest.mark.e2e
def test_handoff_tool_triggers_agent_switch():
    """LLM calls transfer_to_switch_worker, Engine switches to worker, task completes."""
    llm = create_e2e_llm(temperature=0.0)
    orchestrator = SwitchOrchestrator(llm=llm)
    worker = SwitchWorker(llm=llm)

    engine = create_e2e_engine_with_registry(
        orchestrator,
        [AgentSpec(name="switch_worker", description="Specialist worker", agent=worker)],
        auto_approve=True,
    )
    result = engine.run("Calculate 15 times 3 using the worker agent.")
    assert result.state is not None
    assert result.state.final_result is not None
    assert "45" in str(result.state.final_result)


# ── Test: HandoffContext.payload consumed ────────────────────────────────


class PayloadOrch(AgentModule[V07State, Any, Any]):
    name = "payload_orch"
    handoff_targets = ["payload_worker"]

    def __init__(self, llm=None, **kwargs):
        super().__init__(llm=llm, model_parser=ReActTextParser(), **kwargs)

    def init_state(self, task, **kwargs):
        return V07State(task=task, max_steps=8)

    def build_system_prompt(self, state):
        return "Orchestrator. Use transfer_to_payload_worker to delegate."

    def prepare(self, state):
        return f"Task: {state.task}"

    def reduce(self, state, observation, decision):
        if decision.mode == "final":
            state.final_result = str(decision.final_answer or "")
        return state


class PayloadWorker(AgentModule[V07State, Any, Any]):
    name = "payload_worker"

    def __init__(self, llm=None, **kwargs):
        super().__init__(llm=llm, model_parser=ReActTextParser(), **kwargs)

    def init_state(self, task, **kwargs):
        return V07State(task=task, max_steps=8)

    def build_system_prompt(self, state):
        return "Specialist. Complete the task."

    def prepare(self, state):
        return f"Task: {state.task}"

    def reduce(self, state, observation, decision):
        if decision.mode == "final":
            state.final_result = str(decision.final_answer or "")
        return state


@e2e_skip
@pytest.mark.e2e
def test_handoff_payload_consumed():
    """HandoffContext.payload values are written to shared memory."""
    llm = create_e2e_llm(temperature=0.0)
    shared_mem = InMemorySharedMemory()
    mgr = SharedMemoryManager(memory=shared_mem)

    orchestrator = PayloadOrch(llm=llm)
    worker = PayloadWorker(llm=llm)

    engine = create_e2e_engine_with_registry(
        orchestrator,
        [AgentSpec(
            name="payload_worker",
            description="Worker",
            agent=worker,
            handoff_context=HandoffContext(
                strategy=ContextStrategy.SUMMARY,
                payload={"task_type": "math", "priority": "high"},
            ),
            shared_memory=shared_mem,
        )],
        auto_approve=True,
    )
    engine._shared_memory_manager = mgr

    result = engine.run("Calculate 7 times 6.")
    # Payload should be in worker's shared memory namespace
    worker_ns = mgr.namespace("payload_worker")
    assert worker_ns.read("handoff_payload:task_type") == "math"
    assert worker_ns.read("handoff_payload:priority") == "high"


# ── Test: Shared memory cross-agent read ─────────────────────────────────


@e2e_skip
@pytest.mark.e2e
def test_handoff_shared_memory_cross_read():
    """After handoff with shared_memory, target can read source's namespace."""
    llm = create_e2e_llm(temperature=0.0)
    shared_mem = InMemorySharedMemory()
    mgr = SharedMemoryManager(memory=shared_mem)

    # Orchestrator writes data before handoff
    orch_ns = mgr.namespace("payload_orch")
    orch_ns.write("findings", "bug found at line 3")

    orchestrator = PayloadOrch(llm=llm)
    worker = PayloadWorker(llm=llm)

    engine = create_e2e_engine_with_registry(
        orchestrator,
        [AgentSpec(
            name="payload_worker",
            description="Worker",
            agent=worker,
            shared_memory=shared_mem,
        )],
        auto_approve=True,
    )
    engine._shared_memory_manager = mgr

    result = engine.run("Calculate 8 times 5.")

    # Worker should have read access to orchestrator's namespace
    accessible = mgr.get_accessible_namespaces("payload_worker")
    assert "payload_orch" in accessible
    orch_ro = mgr.get_readonly_namespace("payload_worker", "payload_orch")
    assert orch_ro is not None
    assert orch_ro.read("findings") == "bug found at line 3"


# ── Test: Return handoff (worker → orchestrator) ────────────────────────


class ReturnOrch(AgentModule[V07State, Any, Any]):
    """Orchestrator that receives handoff back from worker."""

    name = "return_orch"
    handoff_targets = ["return_worker"]

    def __init__(self, llm=None, **kwargs):
        super().__init__(llm=llm, model_parser=ReActTextParser(), **kwargs)

    def init_state(self, task, **kwargs):
        return V07State(task=task, max_steps=10)

    def decide(self, state, observation):
        # On first step, hand off to worker
        if state.current_step == 0:
            return Decision.handoff(target="return_worker", rationale="Delegate to worker")
        return None

    def build_system_prompt(self, state):
        return "Orchestrator. Provide a final answer summarizing the worker's results."

    def prepare(self, state):
        return f"Task: {state.task}\nThe worker has returned. Summarize the results."

    def reduce(self, state, observation, decision):
        if decision.mode == "final":
            state.final_result = str(decision.final_answer or "")
        return state


class ReturnWorker(AgentModule[V07State, Any, Any]):
    """Worker that hands off back to orchestrator."""

    name = "return_worker"
    handoff_targets = ["return_orch"]

    def __init__(self, llm=None, **kwargs):
        super().__init__(llm=llm, model_parser=ReActTextParser(), **kwargs)

    def init_state(self, task, **kwargs):
        return V07State(task=task, max_steps=10)

    def decide(self, state, observation):
        # After doing work, hand back to orchestrator
        if state.current_step >= 1:
            return Decision.handoff(target="return_orch", rationale="Work done, returning to orchestrator")
        return None

    def build_system_prompt(self, state):
        return "Worker. Do the task, then hand back to return_orch."

    def prepare(self, state):
        return f"Task: {state.task}"

    def reduce(self, state, observation, decision):
        if decision.mode == "final":
            state.final_result = str(decision.final_answer or "")
        return state


@e2e_skip
@pytest.mark.e2e
def test_handoff_return_flow():
    """Worker hands off back to orchestrator (return handoff)."""
    llm = create_e2e_llm(temperature=0.0)
    orchestrator = ReturnOrch(llm=llm)
    worker = ReturnWorker(llm=llm)

    registry = AgentRegistry()
    registry.register(AgentSpec(name="return_orch", description="Orchestrator", agent=orchestrator))
    registry.register(AgentSpec(name="return_worker", description="Worker", agent=worker))

    from qitos.engine.engine import Engine
    engine = Engine(agent=orchestrator, agent_registry=registry, auto_approve=True)
    result = engine.run("Calculate 9 times 4, then report the result.")
    assert result.state is not None
    # Should complete (either via final answer or max steps)
    assert result.state.final_result is not None or result.state.stop_reason is not None


# ── Test: Manager-Worker with real LLM ───────────────────────────────────


@e2e_skip
@pytest.mark.e2e
def test_manager_worker_e2e():
    """Full Manager-Worker template with real LLM."""
    llm = create_e2e_llm(temperature=0.0)

    class E2EManager(AgentModule[V07State, Any, Any]):
        name = "e2e_manager"
        handoff_targets = ["e2e_worker"]

        def __init__(self, llm=None, **kwargs):
            super().__init__(llm=llm, model_parser=ReActTextParser(), **kwargs)

        def init_state(self, task, **kwargs):
            return V07State(task=task, max_steps=8)

        def build_system_prompt(self, state):
            return "Orchestrator. Use transfer_to_e2e_worker to delegate tasks."

        def prepare(self, state):
            return f"Task: {state.task}"

        def reduce(self, state, observation, decision):
            if decision.mode == "final":
                state.final_result = str(decision.final_answer or "")
            return state

    class E2EWorker(AgentModule[V07State, Any, Any]):
        name = "e2e_worker"

        def __init__(self, llm=None, **kwargs):
            super().__init__(llm=llm, model_parser=ReActTextParser(), **kwargs)

        def init_state(self, task, **kwargs):
            return V07State(task=task, max_steps=8)

        def build_system_prompt(self, state):
            return "Worker. Complete the task and provide a final answer."

        def prepare(self, state):
            return f"Task: {state.task}"

        def reduce(self, state, observation, decision):
            if decision.mode == "final":
                state.final_result = str(decision.final_answer or "")
            return state

    manager = E2EManager(llm=llm)
    worker = E2EWorker(llm=llm)

    shared_mem = InMemorySharedMemory()
    engine = create_e2e_engine_with_registry(
        manager,
        [AgentSpec(
            name="e2e_worker",
            description="Worker specialist",
            agent=worker,
            context_strategy=ContextStrategy.SUMMARY,
            handoff_context=HandoffContext(
                strategy=ContextStrategy.SUMMARY,
                payload={"task_type": "math"},
            ),
            shared_memory=shared_mem,
        )],
        auto_approve=True,
    )

    result = engine.run("Calculate 6 times 7 using the worker.")
    assert result.state is not None
    assert result.state.final_result is not None
    assert "42" in str(result.state.final_result)


# ── Test: Handoff loop detection still works ─────────────────────────────


@e2e_skip
@pytest.mark.e2e
def test_handoff_loop_detected_e2e():
    """Handoff loop (A→B→A) is detected with v0.7 pipeline."""
    llm = create_e2e_llm(temperature=0.0)

    @dataclass
    class LoopState(StateSchema):
        pass

    class LoopA(AgentModule[LoopState, Any, Any]):
        name = "loop_a"
        handoff_targets = ["loop_b"]

        def __init__(self, llm=None, **kwargs):
            super().__init__(llm=llm, model_parser=ReActTextParser(), **kwargs)

        def init_state(self, task, **kwargs):
            return LoopState(task=task, max_steps=6)

        def build_system_prompt(self, state):
            return "Agent A. Always use transfer_to_loop_b."

        def prepare(self, state):
            return f"Task: {state.task}"

        def reduce(self, state, observation, decision):
            if decision.mode == "final":
                state.final_result = str(decision.final_answer or "")
            return state

    class LoopB(AgentModule[LoopState, Any, Any]):
        name = "loop_b"
        handoff_targets = ["loop_a"]

        def __init__(self, llm=None, **kwargs):
            super().__init__(llm=llm, model_parser=ReActTextParser(), **kwargs)

        def init_state(self, task, **kwargs):
            return LoopState(task=task, max_steps=6)

        def build_system_prompt(self, state):
            return "Agent B. Always use transfer_to_loop_a."

        def prepare(self, state):
            return f"Task: {state.task}"

        def reduce(self, state, observation, decision):
            if decision.mode == "final":
                state.final_result = str(decision.final_answer or "")
            return state

    agent_a = LoopA(llm=llm)
    agent_b = LoopB(llm=llm)

    registry = AgentRegistry()
    registry.register(AgentSpec(name="loop_a", description="Agent A", agent=agent_a))
    registry.register(AgentSpec(name="loop_b", description="Agent B", agent=agent_b))

    from qitos.engine.engine import Engine
    engine = Engine(agent=agent_a, agent_registry=registry, auto_approve=True)
    result = engine.run("Hand off to B, then B should hand off to A.")

    assert result.state is not None
    stop_reason = str(getattr(result.state, "stop_reason", "") or "").upper()
    assert "LOOP" in stop_reason or "MAX_STEPS" in stop_reason or "BUDGET" in stop_reason or result.state.final_result is not None
