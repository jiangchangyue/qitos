"""Functional (@critic) version of GracefulShutdownCritic.

Forces agents to wrap up near the iteration limit by injecting guidance
telling the agent to call its barrier tool immediately.
"""

from __future__ import annotations

from typing import Any

from qitos.engine.critic_decorator import critic
from qitos.engine.critic_result import CriticResult


def make_graceful_shutdown_critic(shutdown_zone_steps: int = 3):
    """Create a functional graceful-shutdown critic with configurable parameters.

    Returns a Critic instance built with the @critic decorator, preserving
    the same behaviour as GracefulShutdownCritic.

    Parameters
    ----------
    shutdown_zone_steps : int
        Number of steps before max_steps at which to trigger shutdown guidance.
    """

    @critic(name="graceful_shutdown")
    def graceful_shutdown_critic(state, decision, results):
        # If the agent already set final_result, let it finish
        final_result = getattr(state, 'final_result', None)
        if isinstance(final_result, str) and final_result:
            return CriticResult(action="continue", reason="final_result set", score=1.0)

        current_step = getattr(state, 'current_step', 0) or 0
        max_steps = getattr(state, 'max_steps', 0) or 0
        if max_steps <= 0:
            return CriticResult(action="continue", reason="", score=1.0)

        steps_remaining = max_steps - current_step
        if steps_remaining > shutdown_zone_steps:
            return CriticResult(action="continue", reason="", score=1.0)

        # Agent is in the shutdown zone — force it to wrap up
        return CriticResult(
            action="retry",
            reason=f"Approaching step limit ({steps_remaining} steps remaining). "
            "Must produce a result immediately.",
            score=0.1,
            instruction_patch=(
                f"CRITICAL: You have only {steps_remaining} step(s) remaining before the iteration limit.\n"
                "You MUST immediately call your barrier/completion tool (e.g., done, hack_result, "
                "code_result, maintenance_result, search_result, memorist_result, report_result) "
                "to produce a final result. Do NOT attempt any more tool calls — just summarize "
                "what you have accomplished and submit it now."
            ),
        )

    return graceful_shutdown_critic


__all__ = ["make_graceful_shutdown_critic", "graceful_shutdown_critic"]
