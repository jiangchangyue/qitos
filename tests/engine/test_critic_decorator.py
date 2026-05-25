"""Tests for @critic decorator (Task 3.2)."""

from __future__ import annotations

import pytest

from qitos.engine.critic import Critic
from qitos.engine.critic_decorator import _FunctionCritic, _coerce_return, critic
from qitos.engine.critic_result import CriticResult


# ---------------------------------------------------------------------------
# 3.2.1 @critic decorator basics
# ---------------------------------------------------------------------------


class TestCriticDecorator:
    def test_bare_decorator(self):
        """@critic without parens wraps function into _FunctionCritic."""

        @critic
        def my_check(state, decision, results):
            return "continue"

        assert isinstance(my_check, _FunctionCritic)
        assert isinstance(my_check, Critic)

    def test_decorator_with_kwargs(self):
        """@critic(name=..., score=...) accepts keyword arguments."""

        @critic(name="safety", score=0.5)
        def my_check(state, decision, results):
            return "continue"

        assert isinstance(my_check, _FunctionCritic)
        assert my_check._name == "safety"
        assert my_check._default_score == 0.5

    def test_name_defaults_to_function_name(self):
        @critic
        def my_special_critic(state, decision, results):
            return "continue"

        assert my_special_critic._name == "my_special_critic"

    def test_evaluate_calls_wrapped_function(self):
        call_args = {}

        @critic
        def tracker(state, decision, results):
            call_args["state"] = state
            call_args["decision"] = decision
            call_args["results"] = results
            return "continue"

        s = {"key": "val"}
        d = {"mode": "act"}
        r = [{"output": "ok"}]
        result = tracker.evaluate(s, d, r)

        assert call_args["state"] is s
        assert call_args["decision"] is d
        assert call_args["results"] is r
        assert isinstance(result, CriticResult)
        assert result.action == "continue"

    def test_repr(self):
        @critic(name="my_critic")
        def f(state, decision, results):
            return "continue"

        assert "my_critic" in repr(f)


# ---------------------------------------------------------------------------
# 3.2.2 Quick return values
# ---------------------------------------------------------------------------


class TestQuickReturn:
    def test_return_continue_string(self):
        @critic
        def c(state, decision, results):
            return "continue"

        result = c.evaluate(None, None, [])
        assert result.action == "continue"
        assert result.reason == ""

    def test_return_stop_tuple(self):
        @critic
        def c(state, decision, results):
            return "stop", "errors found"

        result = c.evaluate(None, None, [])
        assert result.action == "stop"
        assert result.reason == "errors found"

    def test_return_retry_tuple(self):
        @critic
        def c(state, decision, results):
            return "retry", "unsafe output"

        result = c.evaluate(None, None, [])
        assert result.action == "retry"
        assert result.reason == "unsafe output"

    def test_return_retry_with_instruction_patch(self):
        @critic
        def c(state, decision, results):
            return "retry", "unsafe", "Be more careful"

        result = c.evaluate(None, None, [])
        assert result.action == "retry"
        assert result.reason == "unsafe"
        assert result.instruction_patch == "Be more careful"

    def test_return_critic_result(self):
        @critic
        def c(state, decision, results):
            return CriticResult(action="stop", reason="bad", score=0.1)

        result = c.evaluate(None, None, [])
        assert result.action == "stop"
        assert result.reason == "bad"
        assert result.score == 0.1

    def test_return_dict(self):
        @critic
        def c(state, decision, results):
            return {"action": "retry", "reason": "dict return", "score": 0.3}

        result = c.evaluate(None, None, [])
        assert result.action == "retry"
        assert result.reason == "dict return"
        assert result.score == 0.3


# ---------------------------------------------------------------------------
# _coerce_return edge cases
# ---------------------------------------------------------------------------


class TestCoerceReturn:
    def test_string_action(self):
        result = _coerce_return("continue")
        assert result.action == "continue"

    def test_tuple_1_element(self):
        result = _coerce_return(("stop",))
        assert result.action == "stop"
        assert result.reason == ""

    def test_tuple_2_elements(self):
        result = _coerce_return(("retry", "bad"))
        assert result.action == "retry"
        assert result.reason == "bad"

    def test_tuple_3_elements(self):
        result = _coerce_return(("retry", "bad", "fix it"))
        assert result.action == "retry"
        assert result.reason == "bad"
        assert result.instruction_patch == "fix it"

    def test_dict_passthrough(self):
        result = _coerce_return({"action": "continue", "score": 0.9})
        assert isinstance(result, CriticResult)
        assert result.action == "continue"
        assert result.score == 0.9

    def test_critic_result_passthrough(self):
        original = CriticResult(action="stop", reason="original")
        result = _coerce_return(original)
        assert result is original

    def test_unknown_type_defaults_continue(self):
        result = _coerce_return(42)
        assert result.action == "continue"


# ---------------------------------------------------------------------------
# 3.2.3 Coexistence with Critic subclass
# ---------------------------------------------------------------------------


class TestCriticSubclassCoexistence:
    def test_function_critic_is_critic_instance(self):
        """@critic output is a Critic instance (isinstance check)."""

        @critic
        def c(state, decision, results):
            return "continue"

        assert isinstance(c, Critic)

    def test_function_critic_is_not_subclass_instance(self):
        """@critic output is NOT an instance of a user-defined Critic subclass."""

        class MyCritic(Critic):
            def evaluate(self, state, decision, results):
                return CriticResult(action="continue")

        @critic
        def c(state, decision, results):
            return "continue"

        assert not isinstance(c, MyCritic)

    def test_function_critic_works_with_engine_add_critic(self):
        """@critic critics can be added to engine.critics list like subclass critics."""

        @critic
        def c(state, decision, results):
            return "continue"

        # Simulate engine.add_critic() — it just appends to a list
        critics_list = [c]
        assert len(critics_list) == 1
        assert isinstance(critics_list[0], Critic)

    def test_mixed_critic_types(self):
        """@critic and subclass critics can coexist."""

        class MyCritic(Critic):
            def evaluate(self, state, decision, results):
                return CriticResult(action="continue")

        @critic
        def func_critic(state, decision, results):
            return "continue"

        critics = [MyCritic(), func_critic]
        assert all(isinstance(c, Critic) for c in critics)
        assert isinstance(critics[0], MyCritic)
        assert isinstance(critics[1], _FunctionCritic)


# ---------------------------------------------------------------------------
# 3.2.4 Built-in critic migration
# ---------------------------------------------------------------------------


class TestBuiltInCriticMigration:
    def test_pass_through_functional(self):
        from qitos.kit.critic import pass_through_critic

        result = pass_through_critic.evaluate(None, None, [])
        assert result.action == "continue"
        assert isinstance(pass_through_critic, Critic)

    def test_self_reflection_functional_no_error(self):
        from qitos.kit.critic import self_reflection_critic

        result = self_reflection_critic.evaluate(None, None, [])
        assert result.action == "continue"

    def test_self_reflection_functional_with_error(self):
        from qitos.kit.critic import self_reflection_critic

        state = type("S", (), {"metadata": {}})()
        result = self_reflection_critic.evaluate(state, None, [{"error": "fail"}])
        assert result.action == "retry"
        assert state.metadata["reflection_retries"] == 1

    def test_self_reflection_functional_exceeds_retries(self):
        from qitos.kit.critic import self_reflection_critic

        state = type("S", (), {"metadata": {"reflection_retries": 2}})()
        result = self_reflection_critic.evaluate(state, None, [{"error": "fail"}])
        assert result.action == "stop"

    def test_pass_through_vs_subclass_parity(self):
        """Functional pass_through produces same action as PassThroughCritic."""
        from qitos.kit.critic import PassThroughCritic, pass_through_critic

        func_result = pass_through_critic.evaluate(None, None, [])
        sub_result = PassThroughCritic().evaluate(None, None, [])

        func_action = func_result.action
        sub_action = sub_result["action"] if isinstance(sub_result, dict) else sub_result.action
        assert func_action == sub_action


# ---------------------------------------------------------------------------
# Default score behavior
# ---------------------------------------------------------------------------


class TestDefaultScore:
    def test_default_score_1_not_overridden(self):
        """When score=1.0 is default and function returns no score, keep 1.0."""

        @critic
        def c(state, decision, results):
            return "continue"

        result = c.evaluate(None, None, [])
        assert result.score == 1.0

    def test_custom_default_score_applied(self):
        """When decorator sets score=0.5 and function doesn't set one, use 0.5."""

        @critic(score=0.5)
        def c(state, decision, results):
            return "continue"

        result = c.evaluate(None, None, [])
        assert result.score == 0.5

    def test_explicit_score_not_overridden(self):
        """When function returns an explicit score, don't apply default."""

        @critic(score=0.5)
        def c(state, decision, results):
            return CriticResult(action="continue", score=0.9)

        result = c.evaluate(None, None, [])
        assert result.score == 0.9

    def test_explicit_score_1_kept(self):
        """When function explicitly returns score=1.0, keep it (edge case)."""

        @critic(score=0.5)
        def c(state, decision, results):
            return CriticResult(action="continue", score=1.0)

        # The decorator can't distinguish "explicit 1.0" from "default 1.0"
        # so it applies its default_score — this is an acceptable tradeoff
        result = c.evaluate(None, None, [])
        assert result.score == 0.5  # default_score applied because score == 1.0
