"""Functional (@critic) version of StuckDetectionCritic.

Detects when an agent is stuck in a loop or making no progress.
Monitors for consecutive identical actions and no new findings.
"""

from __future__ import annotations

from typing import Any, List, Optional

from qitos.engine.critic_decorator import critic
from qitos.engine.critic_result import CriticResult


def _action_signature(decision) -> str:
    """Create a signature for the current action to detect loops."""
    if not decision.actions:
        return ""
    parts = []
    for action in (decision.actions or []):
        if isinstance(action, dict):
            tool_name = action.get("tool", action.get("name", ""))
            args_str = str(sorted(action.get("args", action.get("arguments", {})).items()))
            parts.append(f"{tool_name}:{args_str}")
        else:
            parts.append(str(action))
    return "|".join(parts)


def make_stuck_detection_critic(
    max_identical_actions: int = 3,
    max_steps_without_progress: int = 5,
):
    """Create a functional stuck-detection critic with configurable parameters.

    Returns a Critic instance built with the @critic decorator, preserving
    the same behaviour as StuckDetectionCritic.

    Parameters
    ----------
    max_identical_actions : int
        Number of consecutive identical actions before declaring stuck.
    max_steps_without_progress : int
        Number of steps without new findings before declaring no progress.
    """
    # Mutable state via closure
    _action_history: list[str] = []
    _last_finding_step = [0]
    _last_state_size = [0]

    @critic(name="stuck_detection")
    def stuck_detection_critic(state, decision, results):
        # If the agent already set final_result, don't interfere
        final_result = getattr(state, 'final_result', None)
        if isinstance(final_result, str) and final_result:
            return CriticResult(action="continue", reason="final_result set", score=1.0)

        current_step = getattr(state, 'current_step', 0) or 0

        # Track actions
        action_sig = _action_signature(decision)
        if action_sig:
            _action_history.append(action_sig)

        # Check for consecutive identical actions
        if _detect_identical_loop(_action_history, max_identical_actions):
            return CriticResult(
                action="retry",
                reason=f"Detected {max_identical_actions}+ consecutive identical actions. "
                "The current approach is not making progress.",
                score=0.2,
                instruction_patch=(
                    "DETECTED: You are repeating the same action without success.\n"
                    "PIVOT STRATEGY:\n"
                    "1. Stop the current approach — it is not working\n"
                    "2. Try a completely different technique or tool\n"
                    "3. If a tool is failing, try an alternative tool\n"
                    "4. Consider delegating to a specialist for help\n"
                    "5. Use the 'done' tool if the subtask cannot be completed\n"
                ),
                state_patch={"_stuck_detected": True},
            )

        # Check for no progress based on findings in state
        if _detect_no_progress(
            state, current_step, max_steps_without_progress,
            _last_finding_step, _last_state_size,
        ):
            return CriticResult(
                action="retry",
                reason=f"No new findings in {max_steps_without_progress} steps. "
                "Consider changing strategy.",
                score=0.3,
                instruction_patch=(
                    "PROGRESS WARNING: No new findings in recent steps.\n"
                    "SUGGESTED ACTIONS:\n"
                    "1. Try a different angle or technique\n"
                    "2. Search for information about the target\n"
                    "3. Ask the adviser for strategic guidance\n"
                    "4. Move on to the next subtask if current one is blocked\n"
                ),
            )

        return CriticResult(
            action="continue",
            reason="Agent is making progress.",
            score=1.0,
        )

    return stuck_detection_critic


def _detect_identical_loop(
    action_history: list[str], max_identical: int,
) -> bool:
    """Check if the last N actions are identical."""
    if len(action_history) < max_identical:
        return False
    recent = action_history[-max_identical:]
    return len(set(recent)) == 1 and recent[0] != ""


def _detect_no_progress(
    state: Any,
    current_step: int,
    max_no_progress: int,
    last_finding_step: list[int],
    last_state_size: list[int],
) -> bool:
    """Check if there has been no progress for too many steps.

    Updates the mutable closure lists in place.
    """
    if current_step < max_no_progress:
        return False
    findings = getattr(state, 'findings', None)
    scratchpad = getattr(state, 'scratchpad', None)
    current_size = 0
    if isinstance(findings, list):
        current_size += len(findings)
    if isinstance(scratchpad, list):
        current_size += len(scratchpad)
    if current_size > last_state_size[0]:
        last_finding_step[0] = current_step
        last_state_size[0] = current_size
    if current_step - last_finding_step[0] > max_no_progress:
        return True
    return False


__all__ = ["make_stuck_detection_critic", "stuck_detection_critic"]
