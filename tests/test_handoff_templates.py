"""Tests for v0.7 canonical multi-agent templates (mock LLM)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock

import pytest

from qitos import AgentModule, AgentRegistry, AgentSpec, ContextStrategy, Decision, StateSchema
from qitos.core.agent_spec import HandoffContext, StateAdapter
from qitos.core.shared_memory import InMemorySharedMemory, SharedMemoryManager
from qitos.engine.engine import Engine


# ── Manager-Worker template test ─────────────────────────────────────────


@dataclass
class MWState(StateSchema):
    current_agent: str = "manager"


class MWManager(AgentModule[MWState, Any, Any]):
    name = "mw_manager"

    def init_state(self, task, **kwargs):
        return MWState(task=task, max_steps=6)

    def decide(self, state, observation):
        if state.current_step == 0:
            return Decision.handoff(
                target="mw_worker",
                rationale="Delegate to worker",
                handoff_message="Fix the bug",
                handoff_memory_keys=["progress"],
            )
        return None

    def reduce(self, state, observation, decision):
        if decision.mode == "final":
            state.final_result = str(decision.final_answer or "")
        return state


class MWWorker(AgentModule[MWState, Any, Any]):
    name = "mw_worker"

    def init_state(self, task, **kwargs):
        return MWState(task=task, max_steps=6)

    def decide(self, state, observation):
        return Decision.final(answer="Task complete")

    def reduce(self, state, observation, decision):
        if decision.mode == "final":
            state.final_result = str(decision.final_answer or "")
        return state


class TestManagerWorkerTemplate:
    def test_manager_worker_handoff_completes(self):
        llm = MagicMock()
        shared_mem = InMemorySharedMemory()
        manager = MWManager(llm=llm)
        worker = MWWorker(llm=llm)

        registry = AgentRegistry()
        registry.register(AgentSpec(
            name="mw_manager", description="Manager", agent=manager,
        ))
        registry.register(AgentSpec(
            name="mw_worker",
            description="Worker",
            agent=worker,
            context_strategy=ContextStrategy.SUMMARY,
            handoff_context=HandoffContext(
                strategy=ContextStrategy.SUMMARY,
                payload={"task_type": "bug_fix"},
            ),
            shared_memory=shared_mem,
        ))

        engine = Engine(agent=manager, agent_registry=registry, auto_approve=True)
        result = engine.run("Fix the bug", max_steps=6)
        assert result.state is not None
        assert result.state.final_result is not None

    def test_manager_worker_shared_memory_accessible(self):
        llm = MagicMock()
        shared_mem = InMemorySharedMemory()
        mgr = SharedMemoryManager(memory=shared_mem)

        manager = MWManager(llm=llm)
        worker = MWWorker(llm=llm)

        # Manager writes progress before handoff
        mgr.namespace("mw_manager").write("progress", "50%")

        registry = AgentRegistry()
        registry.register(AgentSpec(name="mw_manager", description="Manager", agent=manager))
        registry.register(AgentSpec(
            name="mw_worker", description="Worker", agent=worker,
            shared_memory=shared_mem,
        ))

        engine = Engine(agent=manager, agent_registry=registry, auto_approve=True)
        engine._shared_memory_manager = mgr

        result = engine.run("Fix the bug", max_steps=6)

        # Worker should have read access to manager's namespace
        accessible = mgr.get_accessible_namespaces("mw_worker")
        assert "mw_manager" in accessible


# ── Planner-Executor template test ───────────────────────────────────────


@dataclass
class PlannerSt(StateSchema):
    plan_steps: list[str] = field(default_factory=list)


@dataclass
class ExecutorSt(StateSchema):
    plan_steps: list[str] = field(default_factory=list)
    current_plan_step: int = 0


class PlannerToExec(StateAdapter[PlannerSt, ExecutorSt]):
    def adapt(self, source: PlannerSt) -> ExecutorSt:
        return ExecutorSt(
            task=source.task,
            max_steps=source.max_steps,
            plan_steps=list(source.plan_steps),
        )


class PEPlanner(AgentModule[PlannerSt, Any, Any]):
    name = "pe_planner"

    def init_state(self, task, **kwargs):
        return PlannerSt(task=task, max_steps=8)

    def decide(self, state, observation):
        if state.current_step == 0:
            state.plan_steps = ["Read code", "Fix bug", "Verify"]
            return Decision.handoff(target="pe_executor", rationale="Plan ready")
        return None

    def reduce(self, state, observation, decision):
        return state


class PEExecutor(AgentModule[ExecutorSt, Any, Any]):
    name = "pe_executor"

    def init_state(self, task, **kwargs):
        return ExecutorSt(task=task, max_steps=8)

    def decide(self, state, observation):
        return Decision.final(answer="Plan executed")

    def reduce(self, state, observation, decision):
        if decision.mode == "final":
            state.final_result = str(decision.final_answer or "")
        return state


class TestPlannerExecutorTemplate:
    def test_planner_executor_handoff_completes(self):
        llm = MagicMock()
        planner = PEPlanner(llm=llm)
        executor = PEExecutor(llm=llm)

        registry = AgentRegistry()
        registry.register(AgentSpec(name="pe_planner", description="Planner", agent=planner))
        registry.register(AgentSpec(
            name="pe_executor", description="Executor", agent=executor,
            context_strategy=ContextStrategy.FULL,
            state_adapter=PlannerToExec(),
        ))

        engine = Engine(agent=planner, agent_registry=registry, auto_approve=True)
        result = engine.run("Fix the bug", max_steps=8)
        assert result.state is not None

    def test_state_adapter_converts_plan(self):
        adapter = PlannerToExec()
        source = PlannerSt(task="test", max_steps=10, plan_steps=["step1", "step2"])
        adapted = adapter.adapt(source)
        assert isinstance(adapted, ExecutorSt)
        assert adapted.plan_steps == ["step1", "step2"]
        assert adapted.task == "test"


# ── Proposer-Verifier template test ──────────────────────────────────────


@dataclass
class PVState(StateSchema):
    proposal_count: int = 0
    verified: bool = False


class PVProposer(AgentModule[PVState, Any, Any]):
    name = "pv_proposer"

    def init_state(self, task, **kwargs):
        return PVState(task=task, max_steps=10)

    def decide(self, state, observation):
        if state.current_step == 0:
            return Decision.handoff(target="pv_verifier", rationale="Proposed fix")
        return None

    def reduce(self, state, observation, decision):
        return state


class PVVerifier(AgentModule[PVState, Any, Any]):
    name = "pv_verifier"

    def init_state(self, task, **kwargs):
        return PVState(task=task, max_steps=10)

    def decide(self, state, observation):
        return Decision.final(answer="Verified and accepted")

    def reduce(self, state, observation, decision):
        if decision.mode == "final":
            state.final_result = str(decision.final_answer or "")
            state.verified = True
        return state


class TestProposerVerifierTemplate:
    def test_proposer_verifier_handoff_completes(self):
        llm = MagicMock()
        shared_mem = InMemorySharedMemory()

        proposer = PVProposer(llm=llm)
        verifier = PVVerifier(llm=llm)

        registry = AgentRegistry()
        registry.register(AgentSpec(name="pv_proposer", description="Proposer", agent=proposer))
        registry.register(AgentSpec(
            name="pv_verifier", description="Verifier", agent=verifier,
            context_strategy=ContextStrategy.SUMMARY,
            shared_memory=shared_mem,
        ))

        engine = Engine(agent=proposer, agent_registry=registry, auto_approve=True)
        result = engine.run("Propose and verify a fix", max_steps=10)
        assert result.state is not None
        assert result.state.verified is True
