"""Functional (@critic) version of ReflectorCritic.

Enforces tool-call-only communication with optional LLM-based guidance.
When an agent produces free text instead of a tool call, this critic
generates guidance (via LLM or rule-based fallback) and retries.
"""

from __future__ import annotations

import datetime
from typing import Any, List, Optional

from qitos.engine.critic_decorator import critic
from qitos.engine.critic_result import CriticResult

from ..prompts.reflector_prompt import REFLECTOR_SYSTEM_PROMPT, REFLECTOR_QUESTION_PROMPT


def _generate_llm_guidance(
    llm: Any,
    agent_message: str,
    barrier_tools: List[str],
    execution_context: str,
) -> Optional[str]:
    """Generate reflector guidance via LLM call."""
    if llm is None:
        return None

    try:
        barrier_tools_xml = "\n".join(
            f"  <tool><name>{name}</name></tool>"
            for name in barrier_tools
        )
        barrier_tool_names_xml = "\n".join(
            f"    <tool>{name}</tool>"
            for name in barrier_tools
        )
        current_time = datetime.datetime.now().isoformat()
        request_section = ""

        system_prompt = REFLECTOR_SYSTEM_PROMPT.format(
            barrier_tools=barrier_tools_xml,
            execution_context=execution_context,
            request_section=request_section,
        )

        user_prompt = REFLECTOR_QUESTION_PROMPT.format(
            barrier_tool_names=barrier_tool_names_xml,
            message=agent_message,
        )

        if hasattr(llm, 'invoke'):
            response = llm.invoke(system_prompt + "\n\n" + user_prompt)
            return str(response)
        elif hasattr(llm, 'predict'):
            response = llm.predict(user_prompt, system_prompt=system_prompt)
            return str(response)
        elif hasattr(llm, 'generate'):
            response = llm.generate([system_prompt, user_prompt])
            return str(response)
        elif callable(llm):
            response = llm(user_prompt)
            return str(response)
    except Exception:
        pass

    return None


_RULE_BASED_GUIDANCE = (
    "IMPORTANT: You MUST use a tool call. Free text responses are NOT allowed. "
    "Available options:\n"
    "- Use 'done' tool with a summary when your subtask is complete\n"
    "- Use 'ask_user' tool if you need clarification\n"
    "- Delegate to a specialist agent using the appropriate delegation tool\n"
    "- Use terminal, file, or search tools to take action\n"
    "NEVER respond with plain text — always use a tool call."
)


def make_reflector_critic(
    llm: Any = None,
    max_retries: int = 3,
    barrier_tools: Optional[List[str]] = None,
    execution_context: Optional[str] = None,
):
    """Create a functional reflector critic with configurable parameters.

    Returns a Critic instance built with the @critic decorator, preserving
    the same behaviour as ReflectorCritic.

    Parameters
    ----------
    llm : Any | None
        Optional LLM instance for generating reflector guidance.
    max_retries : int
        Maximum number of reflector retries before stopping.
    barrier_tools : list[str] | None
        Names of barrier tools available to the agent.
    execution_context : str | None
        Current execution context to include in reflector prompt.
    """
    _barrier_tools = barrier_tools or ["done"]
    _execution_context = execution_context or ""
    # Mutable state via closure
    _retry_count = [0]

    @critic(name="reflector")
    def reflector_critic(state, decision, results):
        # If the agent already set final_result, let it finish
        final_result = getattr(state, 'final_result', None)
        if isinstance(final_result, str) and final_result:
            return CriticResult(action="continue", reason="final_result set", score=1.0)

        # Check if the decision has any actions (tool calls)
        has_actions = bool(decision.actions) if decision.actions else False

        if has_actions:
            _retry_count[0] = 0
            return CriticResult(
                action="continue",
                reason="Tool call detected — communication protocol satisfied.",
                score=1.0,
            )

        # No tool calls = free text response, which violates the protocol
        _retry_count[0] += 1

        if _retry_count[0] > max_retries:
            return CriticResult(
                action="stop",
                reason=f"Agent failed to use tool calls after {max_retries} attempts. "
                "Stopping to prevent infinite loop.",
                score=0.0,
            )

        # Extract the agent's free-text message
        agent_message = ""
        if hasattr(decision, 'thought') and decision.thought:
            agent_message = decision.thought
        elif results:
            agent_message = str(results[-1])[:500]

        # Try LLM-based guidance first
        instruction = _generate_llm_guidance(
            llm, agent_message, _barrier_tools, _execution_context,
        )

        # Fall back to rule-based guidance
        if not instruction:
            instruction = _RULE_BASED_GUIDANCE

        return CriticResult(
            action="retry",
            reason="Free text responses are not allowed in this system. "
            "You MUST use a tool call to communicate.",
            score=0.0,
            instruction_patch=instruction,
        )

    return reflector_critic


__all__ = ["make_reflector_critic", "reflector_critic"]
