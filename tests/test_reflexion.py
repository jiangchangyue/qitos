"""Tests for Reflexion method template."""

from __future__ import annotations

import pytest

from qitos.recipes.reflexion import ReflexionAgent, ReflexionCritic, ReflexionState
from qitos.core.decision import Decision
from qitos.core.state import StateSchema
from qitos.engine.critic_result import CriticResult


class TestReflexionState:
    def test_default_values(self) -> None:
        state = ReflexionState(task="test")
        assert state.reflections == []
        assert state.reflection_count == 0
        assert state.max_reflections == 3
        assert state.last_action_success is True
        assert state.attempt == 1


class TestReflexionCritic:
    def test_retry_on_error(self) -> None:
        critic = ReflexionCritic(max_reflections=3)
        state = ReflexionState(task="test")
        decision = Decision(mode="act")
        results = [{"error": "command not found"}]
        result = critic.evaluate(state, decision, results)
        assert result.action == "retry"
        assert result.score == pytest.approx(0.2)
        assert result.instruction_patch is not None
        assert "REFLECTION" in result.instruction_patch
        assert result.state_patch["reflection_count"] == 1
        assert result.state_patch["last_action_success"] is False

    def test_retry_on_nonzero_returncode(self) -> None:
        critic = ReflexionCritic(max_reflections=3)
        state = ReflexionState(task="test")
        decision = Decision(mode="act")
        results = [{"returncode": 1, "output": "error"}]
        result = critic.evaluate(state, decision, results)
        assert result.action == "retry"

    def test_retry_on_empty_results(self) -> None:
        critic = ReflexionCritic(max_reflections=3)
        state = ReflexionState(task="test")
        decision = Decision(mode="act")
        results = []
        result = critic.evaluate(state, decision, results)
        assert result.action == "retry"
        assert result.state_patch["reflection_count"] == 1

    def test_continue_on_success(self) -> None:
        critic = ReflexionCritic(max_reflections=3)
        state = ReflexionState(task="test", last_action_success=True)
        decision = Decision(mode="act")
        results = [{"output": "success result"}]
        result = critic.evaluate(state, decision, results)
        assert result.action == "continue"
        assert result.score >= 0.6

    def test_stop_when_max_reflections_reached(self) -> None:
        critic = ReflexionCritic(max_reflections=2)
        state = ReflexionState(task="test", reflection_count=2)
        decision = Decision(mode="act")
        results = [{"error": "still failing"}]
        result = critic.evaluate(state, decision, results)
        assert result.action == "stop"
        assert result.score == pytest.approx(0.1)

    def test_non_reflexion_state_continues(self) -> None:
        critic = ReflexionCritic()
        state = StateSchema(task="test")
        decision = Decision(mode="act")
        result = critic.evaluate(state, decision, [])
        assert result.action == "continue"

    def test_reflection_content_includes_errors(self) -> None:
        critic = ReflexionCritic()
        state = ReflexionState(task="test")
        decision = Decision(mode="act", rationale="run the tests")
        results = [{"error": "ImportError: no module"}]
        result = critic.evaluate(state, decision, results)
        assert "ImportError" in result.instruction_patch

    def test_state_patch_on_retry(self) -> None:
        critic = ReflexionCritic(max_reflections=3)
        state = ReflexionState(task="test", reflection_count=0)
        decision = Decision(mode="act")
        results = [{"error": "failed"}]
        result = critic.evaluate(state, decision, results)
        assert result.state_patch is not None
        assert result.state_patch["reflection_count"] == 1
        assert result.state_patch["last_action_success"] is False


class TestReflexionAgent:
    def test_init_state(self) -> None:
        agent = ReflexionAgent()
        state = agent.init_state("Debug the test", max_steps=15)
        assert state.task == "Debug the test"
        assert state.max_steps == 15
        assert state.max_reflections == 3

    def test_init_state_custom_reflections(self) -> None:
        agent = ReflexionAgent()
        state = agent.init_state("test", max_steps=5, max_reflections=5)
        assert state.max_reflections == 5

    def test_build_system_prompt(self) -> None:
        agent = ReflexionAgent()
        state = ReflexionState(task="test")
        prompt = agent.build_system_prompt(state)
        assert "Reflexion" in prompt
        assert "Act" in prompt
        assert "Reflect" in prompt

    def test_build_system_prompt_with_reflections(self) -> None:
        agent = ReflexionAgent()
        state = ReflexionState(
            task="test",
            reflections=["Need to fix import path", "Check module structure"],
        )
        prompt = agent.build_system_prompt(state)
        assert "Previous Reflections" in prompt
        assert "fix import path" in prompt

    def test_prepare(self) -> None:
        agent = ReflexionAgent()
        state = ReflexionState(task="Debug the failing test")
        text = agent.prepare(state, {})
        assert "Debug the failing test" in text
        assert "Attempt: 1" in text

    def test_reduce_extracts_final_answer(self) -> None:
        agent = ReflexionAgent()
        state = ReflexionState(task="test")
        decision = Decision(mode="act")
        results = [{"output": "All tests pass. FINAL ANSWER: fixed"}]
        new_state = agent.reduce(state, {}, decision, results)
        assert new_state.final_result == "fixed"

    def test_reduce_tracks_attempts_on_failure(self) -> None:
        agent = ReflexionAgent()
        state = ReflexionState(task="test", last_action_success=False, attempt=1)
        decision = Decision(mode="act")
        new_state = agent.reduce(state, {}, decision, [])
        assert new_state.attempt == 2
