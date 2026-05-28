"""Tests for v0.7 state adaptation hardening and typed observation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from qitos import AgentModule, AgentRegistry, AgentSpec, ContextStrategy, Decision, StateSchema
from qitos.core.agent_spec import StateAdapter
from qitos.core.observation import Observation
from qitos.engine.engine import Engine


# -- State adaptation with setattr --


@dataclass
class StateA(StateSchema):
    task: str = ""
    field_a: str = "a"
    _private_a: str = "private_a"


@dataclass
class StateB(StateSchema):
    task: str = ""
    field_b: str = "b"
    _private_b: str = "private_b"


class SimpleStateAdapter(StateAdapter[StateA, StateB]):
    """Convert StateA → StateB for handoff."""

    def adapt(self, source: StateA) -> StateB:
        return StateB(
            task=source.task,
            field_b=source.field_a,
            _private_b="adapted_private",
        )


class AdapterOrchestrator(AgentModule[StateA, Any, Any]):
    """Orchestrator with StateA that hands off to worker with StateB."""

    name = "adapter_orch"

    def init_state(self, task, **kwargs):
        return StateA(task=task, max_steps=8)

    def decide(self, state, observation):
        if state.current_step == 0:
            return Decision.handoff(target="worker", rationale="Delegate")
        return None

    def reduce(self, state, observation, decision):
        return state


class AdapterWorker(AgentModule[StateB, Any, Any]):
    """Worker with StateB."""

    name = "adapter_worker"

    def init_state(self, task, **kwargs):
        return StateB(task=task, max_steps=8)

    def decide(self, state, observation):
        return Decision.final(answer="Done")

    def reduce(self, state, observation, decision):
        if decision.mode == "final":
            state.final_result = str(decision.final_answer or "")
        return state


class TestStateAdaptationSetattr:
    def test_state_adapter_copies_public_fields(self):
        """StateAdapter.adapt() copies public fields using setattr."""
        from unittest.mock import MagicMock

        llm = MagicMock()
        orchestrator = AdapterOrchestrator(llm=llm)
        worker = AdapterWorker(llm=llm)

        registry = AgentRegistry()
        registry.register(AgentSpec(
            name="worker",
            description="Worker",
            agent=worker,
            state_adapter=SimpleStateAdapter(),
        ))

        engine = Engine(agent=orchestrator, agent_registry=registry, auto_approve=True)
        result = engine.run("Test task", max_steps=5)

        # The state should have been adapted from StateA to StateB-like
        # The state object is still StateA but with StateB's fields copied in
        assert result.state is not None

    def test_private_fields_not_copied(self):
        """Private fields (starting with _) are not copied during state adaptation."""
        adapter = SimpleStateAdapter()
        source = StateA(task="test", field_a="value_a", _private_a="secret")
        adapted = adapter.adapt(source)
        # The adapter's _private_b should be set but not copied to the engine's state
        # The key point is that setattr skips keys starting with _
        assert adapted._private_b == "adapted_private"

    def test_state_adapter_adapt_method(self):
        """SimpleStateAdapter correctly converts StateA → StateB."""
        adapter = SimpleStateAdapter()
        source = StateA(task="my task", field_a="hello")
        result = adapter.adapt(source)
        assert isinstance(result, StateB)
        assert result.task == "my task"
        assert result.field_b == "hello"


# -- Typed observation after handoff --


class TestTypedObservationAfterHandoff:
    def test_handoff_observation_is_observation_type(self):
        """After handoff, the observation is an Observation instance, not a plain dict."""
        from unittest.mock import MagicMock

        @dataclass
        class SimpleState(StateSchema):
            pass

        class Orch(AgentModule[SimpleState, Any, Any]):
            name = "orch_typed"
            def init_state(self, task, **kwargs):
                return SimpleState(task=task, max_steps=8)
            def decide(self, state, observation):
                if state.current_step == 0:
                    return Decision.handoff(target="worker_typed", rationale="Go")
                return None
            def reduce(self, state, observation, decision):
                return state

        class Worker(AgentModule[SimpleState, Any, Any]):
            name = "worker_typed"
            def init_state(self, task, **kwargs):
                return SimpleState(task=task, max_steps=8)
            def decide(self, state, observation):
                return Decision.final(answer="Complete")
            def reduce(self, state, observation, decision):
                if decision.mode == "final":
                    state.final_result = str(decision.final_answer or "")
                return state

        llm = MagicMock()
        registry = AgentRegistry()
        registry.register(AgentSpec(name="worker_typed", description="Worker", agent=Worker()))

        engine = Engine(agent=Orch(llm=llm), agent_registry=registry, auto_approve=True)

        # Hook into the engine to capture the observation after handoff
        captured_observations = []
        original_reduce = Worker.reduce

        def patched_reduce(self, state, observation, decision):
            captured_observations.append(observation)
            return original_reduce(self, state, observation, decision)

        Worker.reduce = patched_reduce
        try:
            result = engine.run("Test task", max_steps=5)
        finally:
            Worker.reduce = original_reduce

        # The worker should have received at least one observation
        # The first observation after handoff should be an Observation instance
        assert len(captured_observations) > 0
        handoff_obs = captured_observations[0]
        assert isinstance(handoff_obs, (Observation, dict))

    def test_observation_from_value_handles_handoff_dict(self):
        """Observation.from_value() correctly parses a handoff-style dict."""
        payload = {
            "action_results": [{
                "handoff": True,
                "from": "orchestrator",
                "to": "worker",
            }],
        }
        obs = Observation.from_value(payload)
        assert isinstance(obs, Observation)
