"""Tests for Self-Refine method template."""

from __future__ import annotations

import pytest

from qitos.recipes.self_refine import SelfRefineAgent, SelfRefineCritic, SelfRefineState
from qitos.core.decision import Decision
from qitos.engine.critic_result import CriticResult


class TestSelfRefineState:
    def test_default_values(self) -> None:
        state = SelfRefineState(task="test")
        assert state.draft == ""
        assert state.refinement_count == 0
        assert state.max_refinements == 3
        assert state.critique_history == []


class TestSelfRefineCritic:
    def test_retry_on_empty_draft(self) -> None:
        critic = SelfRefineCritic(max_refinements=3, quality_threshold=0.7)
        state = SelfRefineState(task="test", draft="")
        decision = Decision(mode="act")
        result = critic.evaluate(state, decision, [])
        assert result.action == "retry"
        assert result.score < 0.7
        assert result.instruction_patch is not None
        assert result.state_patch is not None
        assert result.state_patch["refinement_count"] == 1

    def test_retry_on_short_draft(self) -> None:
        critic = SelfRefineCritic(max_refinements=3, quality_threshold=0.7)
        state = SelfRefineState(task="test", draft="hi", refinement_count=0)
        decision = Decision(mode="act")
        result = critic.evaluate(state, decision, [])
        assert result.action == "retry"
        assert result.score <= 0.3

    def test_continue_when_score_high_enough(self) -> None:
        critic = SelfRefineCritic(max_refinements=3, quality_threshold=0.7)
        # refinement_count=2 with long draft should score >= 0.7
        state = SelfRefineState(
            task="test",
            draft="This is a sufficiently long draft with meaningful content.",
            refinement_count=2,
        )
        decision = Decision(mode="act")
        result = critic.evaluate(state, decision, [])
        assert result.action in ("continue", "stop")
        assert result.score >= 0.7

    def test_stop_when_max_refinements_reached(self) -> None:
        critic = SelfRefineCritic(max_refinements=2, quality_threshold=0.9)
        state = SelfRefineState(
            task="test",
            draft="Some draft",
            refinement_count=2,
        )
        decision = Decision(mode="act")
        result = critic.evaluate(state, decision, [])
        # Even if score < threshold, stop because max refinements reached
        assert result.action == "stop"

    def test_non_self_refine_state_continues(self) -> None:
        critic = SelfRefineCritic()
        from qitos.core.state import StateSchema

        state = StateSchema(task="test")
        decision = Decision(mode="act")
        result = critic.evaluate(state, decision, [])
        assert result.action == "continue"

    def test_state_patch_increments_count(self) -> None:
        critic = SelfRefineCritic(max_refinements=3, quality_threshold=0.8)
        state = SelfRefineState(task="test", draft="short", refinement_count=0)
        decision = Decision(mode="act")
        result = critic.evaluate(state, decision, [])
        assert result.state_patch["refinement_count"] == 1

        state.refinement_count = 1
        result = critic.evaluate(state, decision, [])
        assert result.state_patch["refinement_count"] == 2


class TestSelfRefineAgent:
    def test_init_state(self) -> None:
        agent = SelfRefineAgent()
        state = agent.init_state("Write a summary", max_steps=10)
        assert state.task == "Write a summary"
        assert state.max_steps == 10
        assert state.max_refinements == 3

    def test_init_state_custom_refinements(self) -> None:
        agent = SelfRefineAgent()
        state = agent.init_state("test", max_steps=5, max_refinements=5)
        assert state.max_refinements == 5

    def test_build_system_prompt(self) -> None:
        agent = SelfRefineAgent()
        state = SelfRefineState(task="test")
        prompt = agent.build_system_prompt(state)
        assert "Self-Refine" in prompt
        assert "Generate" in prompt
        assert "Critique" in prompt
        assert "Refine" in prompt

    def test_build_system_prompt_with_refinement(self) -> None:
        agent = SelfRefineAgent()
        state = SelfRefineState(task="test", refinement_count=2)
        prompt = agent.build_system_prompt(state)
        assert "refinement round 2" in prompt

    def test_prepare(self) -> None:
        agent = SelfRefineAgent()
        state = SelfRefineState(task="Write a summary", draft="My draft")
        text = agent.prepare(state, {})
        assert "Write a summary" in text
        assert "My draft" in text

    def test_reduce_extracts_final_answer(self) -> None:
        agent = SelfRefineAgent()
        state = SelfRefineState(task="test")
        decision = Decision(mode="act")
        results = [{"output": "Some text FINAL ANSWER: The answer is 42"}]
        new_state = agent.reduce(state, {}, decision, results)
        assert new_state.draft == "The answer is 42"
        assert new_state.final_result == "The answer is 42"

    def test_reduce_stores_text_as_draft(self) -> None:
        agent = SelfRefineAgent()
        state = SelfRefineState(task="test")
        decision = Decision(mode="act")
        results = [{"output": "A working draft"}]
        new_state = agent.reduce(state, {}, decision, results)
        assert new_state.draft == "A working draft"
