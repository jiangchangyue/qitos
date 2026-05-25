"""Tests for new orchestration patterns — Debate, MoA, Workflow (Task 3.6)."""

from __future__ import annotations

import pytest

from qitos.kit.patterns.debate import DebateConfig, build_debate_system, _DebateModerator
from qitos.kit.patterns.moa import MoAConfig, build_moa_system, _MoAAggregator
from qitos.kit.patterns.workflow import (
    Workflow,
    WorkflowConfig,
    WorkflowState,
    build_workflow_system,
)


# ---------------------------------------------------------------------------
# 3.6.1 Debate pattern
# ---------------------------------------------------------------------------


class TestDebateConfig:
    def test_defaults(self):
        config = DebateConfig()
        assert config.debaters == ["proponent", "opponent"]
        assert config.rounds == 3
        assert config.moderator_name == "moderator"


class TestDebateBuildSystem:
    def test_build_creates_moderator_and_registry(self):
        config = DebateConfig(llm=None)
        moderator, registry = build_debate_system(config)
        assert isinstance(moderator, _DebateModerator)
        assert registry is not None

    def test_custom_debaters(self):
        config = DebateConfig(
            debaters=["for", "against", "neutral"],
            rounds=2,
        )
        moderator, registry = build_debate_system(config)
        assert moderator._config.debaters == ["for", "against", "neutral"]

    def test_moderator_state_init(self):
        config = DebateConfig()
        moderator = _DebateModerator(config)
        state = moderator.init_state("test topic")
        assert state.task == "test topic"
        assert state.current_round == 0
        assert state.arguments == []
        assert state.verdict == ""

    def test_moderator_builds_prompt(self):
        config = DebateConfig(rounds=3)
        moderator = _DebateModerator(config)
        state = moderator.init_state("test")
        prompt = moderator.build_system_prompt(state)
        assert "debate moderator" in prompt.lower() or "moderator" in prompt.lower()


# ---------------------------------------------------------------------------
# 3.6.2 MoA pattern
# ---------------------------------------------------------------------------


class TestMoAConfig:
    def test_defaults(self):
        config = MoAConfig()
        assert config.proposers == ["analyst_a", "analyst_b", "analyst_c"]
        assert config.aggregator_name == "aggregator"


class TestMoABuildSystem:
    def test_build_creates_aggregator_and_registry(self):
        config = MoAConfig(llm=None)
        aggregator, registry = build_moa_system(config)
        assert isinstance(aggregator, _MoAAggregator)
        assert registry is not None

    def test_custom_proposers(self):
        config = MoAConfig(
            proposers=["expert_1", "expert_2"],
            aggregator_max_steps=15,
        )
        aggregator, registry = build_moa_system(config)
        assert aggregator._config.proposers == ["expert_1", "expert_2"]

    def test_aggregator_state_init(self):
        config = MoAConfig()
        aggregator = _MoAAggregator(config)
        state = aggregator.init_state("evaluate X")
        assert state.task == "evaluate X"
        assert state.proposals == []
        assert state.synthesis == ""

    def test_aggregator_builds_prompt(self):
        config = MoAConfig()
        aggregator = _MoAAggregator(config)
        state = aggregator.init_state("test")
        prompt = aggregator.build_system_prompt(state)
        assert "aggregator" in prompt.lower()


# ---------------------------------------------------------------------------
# 3.6.3 Workflow pattern
# ---------------------------------------------------------------------------


class TestWorkflow:
    def test_add_node(self):
        wf = Workflow()
        wf.add_node("start", lambda task, **kw: task)
        assert "start" in wf.nodes

    def test_add_edge(self):
        wf = Workflow()
        wf.add_node("a", lambda task, **kw: "a_result")
        wf.add_node("b", lambda task, **kw: "b_result")
        wf.add_edge("a", "b")
        assert ("a", "b") in wf.edges

    def test_add_edge_unknown_source(self):
        wf = Workflow()
        wf.add_node("b", lambda task, **kw: "b")
        with pytest.raises(ValueError, match="Source node"):
            wf.add_edge("a", "b")

    def test_add_edge_unknown_target(self):
        wf = Workflow()
        wf.add_node("a", lambda task, **kw: "a")
        with pytest.raises(ValueError, match="Target node"):
            wf.add_edge("a", "b")

    def test_linear_workflow(self):
        results = {}

        def step_a(task, **kw):
            results["a"] = f"a_{task}"
            return results["a"]

        def step_b(task, context=None, **kw):
            prev = context.get("a", "") if context else ""
            results["b"] = f"b_{prev}"
            return results["b"]

        wf = Workflow()
        wf.add_node("a", step_a)
        wf.add_node("b", step_b)
        wf.add_edge("a", "b")

        state = wf.run("test")
        assert state.completed_nodes == ["a", "b"]
        assert "a" in state.node_results
        assert "b" in state.node_results

    def test_diamond_workflow(self):
        """Diamond: start -> (left, right) -> end"""
        def start(task, **kw):
            return f"started_{task}"

        def left(task, context=None, **kw):
            return "left_result"

        def right(task, context=None, **kw):
            return "right_result"

        def end(task, context=None, **kw):
            left_r = context.get("left", "") if context else ""
            right_r = context.get("right", "") if context else ""
            return f"end_{left_r}_{right_r}"

        wf = Workflow()
        wf.add_node("start", start)
        wf.add_node("left", left)
        wf.add_node("right", right)
        wf.add_node("end", end)
        wf.add_edge("start", "left")
        wf.add_edge("start", "right")
        wf.add_edge("left", "end")
        wf.add_edge("right", "end")

        state = wf.run("test")
        assert len(state.completed_nodes) == 4
        assert state.node_results["end"] == "end_left_result_right_result"

    def test_cycle_detection(self):
        wf = Workflow()
        wf.add_node("a", lambda task, **kw: "a")
        wf.add_node("b", lambda task, **kw: "b")
        wf.add_edge("a", "b")
        wf.add_edge("b", "a")

        with pytest.raises(ValueError, match="cycle"):
            wf.run("test")

    def test_strict_order_fails_on_error(self):
        def failing(task, **kw):
            raise RuntimeError("boom")

        wf = Workflow()
        wf.add_node("a", failing)
        state = wf.run("test")
        assert "a" in state.errors
        assert state.stop_reason is not None

    def test_non_strict_continues_on_error(self):
        def failing(task, **kw):
            raise RuntimeError("boom")

        def ok(task, **kw):
            return "ok"

        wf = Workflow(WorkflowConfig(strict_order=False))
        wf.add_node("a", failing)
        wf.add_node("b", ok)
        state = wf.run("test")
        assert "a" in state.errors
        assert "b" in state.completed_nodes

    def test_context_receives_upstream_results(self):
        captured = {}

        def step_a(task, **kw):
            return "result_a"

        def step_b(task, context=None, **kw):
            captured["context"] = context
            return "result_b"

        wf = Workflow()
        wf.add_node("a", step_a)
        wf.add_node("b", step_b)
        wf.add_edge("a", "b")

        wf.run("test")
        assert captured["context"]["a"] == "result_a"

    def test_set_entry(self):
        wf = Workflow()
        wf.add_node("start", lambda task, **kw: "s")
        wf.add_node("other", lambda task, **kw: "o")
        wf.set_entry("other")
        assert wf._entry_node == "other"

    def test_chaining_api(self):
        wf = Workflow()
        result = wf.add_node("a", lambda task, **kw: "a")
        assert result is wf


class TestBuildWorkflowSystem:
    def test_creates_workflow(self):
        wf = build_workflow_system()
        assert isinstance(wf, Workflow)

    def test_with_config(self):
        config = WorkflowConfig(max_node_retries=3)
        wf = build_workflow_system(config)
        assert wf._config.max_node_retries == 3


# ---------------------------------------------------------------------------
# Integration: patterns interoperate
# ---------------------------------------------------------------------------


class TestPatternInterop:
    def test_debate_config_sanity(self):
        """Debate config with custom values doesn't crash."""
        config = DebateConfig(
            debaters=["team_a", "team_b", "judge"],
            rounds=5,
            debater_max_steps=3,
        )
        moderator, registry = build_debate_system(config)
        assert moderator._config.rounds == 5

    def test_moa_config_sanity(self):
        """MoA config with custom values doesn't crash."""
        config = MoAConfig(
            proposers=["p1", "p2"],
            aggregator_max_steps=15,
        )
        aggregator, registry = build_moa_system(config)
        assert len(aggregator._config.proposers) == 2

    def test_workflow_with_lambda_nodes(self):
        """Workflow can use simple lambda functions."""
        wf = Workflow()
        wf.add_node("double", lambda task, **kw: task * 2)
        state = wf.run("x")
        assert state.node_results["double"] == "xx"
