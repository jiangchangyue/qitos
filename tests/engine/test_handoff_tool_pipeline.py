"""Tests for v0.7 HandoffTool → Engine pipeline integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List
from unittest.mock import MagicMock

import pytest

from qitos import Action, AgentModule, AgentRegistry, AgentSpec, ContextStrategy, Decision, StateSchema, ToolRegistry
from qitos.kit.tool.handoff_tool import HandoffTool
from qitos.engine.engine import Engine


# -- Shared test fixtures --


@dataclass
class PipeState(StateSchema):
    scratchpad: list[str] = field(default_factory=list)
    current_agent: str = "orchestrator"


class OrchestratorAgent(AgentModule[PipeState, Any, Action]):
    """Orchestrator that hands off to a worker."""

    name = "orchestrator"
    handoff_targets = ["worker"]

    def __init__(self, llm=None, **kwargs):
        super().__init__(llm=llm, **kwargs)

    def init_state(self, task, **kwargs):
        return PipeState(task=task, max_steps=8)

    def decide(self, state, observation):
        if state.current_step == 0:
            return Decision.handoff(target="worker", rationale="Delegate to worker")
        return None

    def reduce(self, state, observation, decision):
        if decision.mode == "final":
            state.final_result = str(decision.final_answer or "")
        return state


class WorkerAgent(AgentModule[PipeState, Any, Action]):
    """Worker that completes the task."""

    name = "worker"

    def __init__(self, llm=None, **kwargs):
        super().__init__(llm=llm, **kwargs)

    def init_state(self, task, **kwargs):
        return PipeState(task=task, max_steps=8)

    def decide(self, state, observation):
        return Decision.final(answer="Task complete")

    def reduce(self, state, observation, decision):
        if decision.mode == "final":
            state.final_result = str(decision.final_answer or "")
        return state


def _make_registry():
    registry = AgentRegistry()
    registry.register(AgentSpec(name="worker", description="Worker agent", agent=WorkerAgent()))
    return registry


# -- Test: HandoffTool enriched parameters --


class TestHandoffToolEnrichedParameters:
    def test_message_parameter_in_spec(self):
        tool = HandoffTool("worker")
        params = tool.spec.parameters
        assert "message" in params
        assert params["message"]["type"] == "string"

    def test_memory_keys_parameter_in_spec(self):
        tool = HandoffTool("worker")
        params = tool.spec.parameters
        assert "memory_keys" in params
        assert params["memory_keys"]["type"] == "array"

    def test_execute_returns_message_and_memory_keys(self):
        tool = HandoffTool("worker")
        result = tool.execute({
            "rationale": "Need help",
            "message": "Please process this",
            "memory_keys": ["progress", "findings"],
        })
        assert result["handoff_target"] == "worker"
        assert result["message"] == "Please process this"
        assert result["memory_keys"] == ["progress", "findings"]

    def test_execute_defaults_empty_message_and_memory_keys(self):
        tool = HandoffTool("worker")
        result = tool.execute({"rationale": "Need help"})
        assert result["message"] == ""
        assert result["memory_keys"] == []

    def test_execute_non_dict_args(self):
        tool = HandoffTool("worker")
        result = tool.execute("not a dict")
        assert result["handoff_target"] == "worker"
        assert result["rationale"] == ""
        assert result["message"] == ""
        assert result["memory_keys"] == []


# -- Test: Decision.handoff() enriched meta --


class TestDecisionHandoffEnrichedMeta:
    def test_handoff_with_message(self):
        d = Decision.handoff(target="worker", handoff_message="Please process this")
        assert d.meta["handoff_target"] == "worker"
        assert d.meta["handoff_message"] == "Please process this"

    def test_handoff_with_memory_keys(self):
        d = Decision.handoff(target="worker", handoff_memory_keys=["progress"])
        assert d.meta["handoff_memory_keys"] == ["progress"]

    def test_handoff_without_optional_fields(self):
        d = Decision.handoff(target="worker")
        assert "handoff_message" not in d.meta
        assert "handoff_memory_keys" not in d.meta

    def test_handoff_with_all_fields(self):
        d = Decision.handoff(
            target="worker",
            rationale="Delegating",
            handoff_message="Context for worker",
            handoff_memory_keys=["key1", "key2"],
            meta={"extra": "data"},
        )
        assert d.meta["handoff_target"] == "worker"
        assert d.meta["handoff_message"] == "Context for worker"
        assert d.meta["handoff_memory_keys"] == ["key1", "key2"]
        assert d.meta["extra"] == "data"


# -- Test: Engine HandoffTool interception --


class TestEngineHandoffToolPipeline:
    def test_check_handoff_from_decision(self):
        """When _action_runtime returns a Decision, _check_handoff detects it."""
        llm = MagicMock()
        orchestrator = OrchestratorAgent(llm=llm)
        registry = _make_registry()
        engine = Engine(agent=orchestrator, agent_registry=registry)

        handoff_decision = Decision.handoff(target="worker", rationale="Test")
        result = engine._check_handoff_from_tool_result(handoff_decision)
        assert result is not None
        assert result.mode == "handoff"
        assert result.meta["handoff_target"] == "worker"

    def test_check_handoff_from_dict_result(self):
        """When HandoffTool.execute() returns a dict, _check_handoff detects it."""
        llm = MagicMock()
        orchestrator = OrchestratorAgent(llm=llm)
        registry = _make_registry()
        engine = Engine(agent=orchestrator, agent_registry=registry)

        action_results = [{
            "handoff_target": "worker",
            "status": "pending",
            "rationale": "Need worker",
            "message": "Context",
            "memory_keys": ["key1"],
        }]
        result = engine._check_handoff_from_tool_result(action_results)
        assert result is not None
        assert result.mode == "handoff"
        assert result.meta["handoff_target"] == "worker"
        assert result.meta["handoff_message"] == "Context"
        assert result.meta["handoff_memory_keys"] == ["key1"]

    def test_check_handoff_no_handoff(self):
        """Normal tool results are not detected as handoff."""
        llm = MagicMock()
        orchestrator = OrchestratorAgent(llm=llm)
        registry = _make_registry()
        engine = Engine(agent=orchestrator, agent_registry=registry)

        action_results = [{"output": "file contents", "status": "success"}]
        result = engine._check_handoff_from_tool_result(action_results)
        assert result is None

    def test_intercept_handoff_action_with_message(self):
        """_intercept_handoff_action passes message and memory_keys."""
        llm = MagicMock()
        orchestrator = OrchestratorAgent(llm=llm)
        registry = _make_registry()
        engine = Engine(agent=orchestrator, agent_registry=registry)

        action = Action(
            name="transfer_to_worker",
            args={
                "rationale": "Need help",
                "message": "Please process this",
                "memory_keys": ["progress"],
            },
        )
        result = engine._intercept_handoff_action(action)
        assert result is not None
        assert result.mode == "handoff"
        assert result.meta["handoff_target"] == "worker"
        assert result.meta["handoff_message"] == "Please process this"
        assert result.meta["handoff_memory_keys"] == ["progress"]

    def test_intercept_handoff_action_not_handoff(self):
        """Non-handoff actions are not intercepted."""
        llm = MagicMock()
        orchestrator = OrchestratorAgent(llm=llm)
        registry = _make_registry()
        engine = Engine(agent=orchestrator, agent_registry=registry)

        action = Action(name="read_file", args={"path": "/tmp/test"})
        result = engine._intercept_handoff_action(action)
        assert result is None

    def test_execute_handoff_step_method_exists(self):
        """_execute_handoff_step is a callable method on Engine."""
        llm = MagicMock()
        orchestrator = OrchestratorAgent(llm=llm)
        registry = _make_registry()
        engine = Engine(agent=orchestrator, agent_registry=registry)
        assert callable(engine._execute_handoff_step)

    def test_full_handoff_via_decide(self):
        """Full Engine.run() with decide()-returned handoff completes."""
        llm = MagicMock()
        llm.call = MagicMock(return_value='Thought: Done\nFinal Answer: Task complete')
        orchestrator = OrchestratorAgent(llm=llm)
        registry = _make_registry()
        engine = Engine(agent=orchestrator, agent_registry=registry, auto_approve=True)
        result = engine.run("Test task", max_steps=5)
        assert result.state is not None

    def test_handoff_tool_registered_in_engine(self):
        """HandoffTools from AgentRegistry are registered in the Engine."""
        llm = MagicMock()
        orchestrator = OrchestratorAgent(llm=llm)
        registry = _make_registry()
        engine = Engine(agent=orchestrator, agent_registry=registry, auto_approve=True)
        tool_names = engine.tool_registry.list_tools()
        assert "transfer_to_worker" in tool_names
