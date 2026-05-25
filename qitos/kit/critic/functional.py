"""Functional (@critic) versions of built-in critics."""

from __future__ import annotations

from qitos.engine.critic_decorator import critic


@critic(name="pass_through")
def pass_through_critic(state, decision, results):
    """Always continue — functional equivalent of PassThroughCritic."""
    return "continue"


@critic(name="self_reflection", score=1.0)
def self_reflection_critic(state, decision, results):
    """Retry on tool errors, stop after max retries.

    Functional equivalent of SelfReflectionCritic(max_retries=2).

    For custom max_retries, write your own @critic with the same pattern::

        @critic(name="my_reflection")
        def my_reflection(state, decision, results):
            metadata = getattr(state, "metadata", {}) or {}
            retries = int(metadata.get("reflection_retries", 0))
            has_error = any(isinstance(r, dict) and r.get("error") for r in results)
            if has_error and retries < 5:
                metadata["reflection_retries"] = retries + 1
                state.metadata = metadata
                return "retry", "tool_error_retry"
            if has_error:
                return "stop", "exceeded_retries"
            return "continue"
    """
    metadata = getattr(state, "metadata", {}) or {}
    retries = int(metadata.get("reflection_retries", 0))

    has_error = any(isinstance(r, dict) and r.get("error") for r in results)
    if has_error and retries < 2:
        metadata["reflection_retries"] = retries + 1
        state.metadata = metadata
        return "retry", "tool_error_retry"

    if has_error:
        return "stop", "exceeded_retries"

    return "continue"


__all__ = ["pass_through_critic", "self_reflection_critic"]
