"""Debate pattern — multi-agent debate with Moderator Agent adjudication.

Usage::

    from qitos.kit.patterns import build_debate_system, DebateConfig

    config = DebateConfig(
        debaters=["proponent", "opponent"],
        rounds=3,
        llm=my_llm,
    )
    moderator, registry = build_debate_system(config)
    result = moderator.run(task="Should AI be regulated?")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ...core.agent_module import AgentModule
from ...core.decision import Decision
from ...core.state import StateSchema
from ...core.channel import Append


@dataclass
class DebateConfig:
    """Configuration for the debate pattern."""

    debaters: List[str] = field(default_factory=lambda: ["proponent", "opponent"])
    rounds: int = 3
    moderator_name: str = "moderator"
    debater_max_steps: int = 3
    moderator_max_steps: int = 20
    llm: Any = None
    workspace_root: str = "."


@dataclass
class DebateState(StateSchema):
    """State for the debate moderator."""

    current_round: int = 0
    arguments: Annotated[List[Dict[str, Any]], Append] = field(default_factory=list)  # noqa: F821
    verdict: str = ""


class _DebaterAgent(AgentModule):
    """A single debater agent."""

    def __init__(self, stance: str, llm: Any = None, **kwargs: Any):
        self._stance = stance
        super().__init__(llm=llm, **kwargs)

    @property
    def name(self) -> str:  # type: ignore[override]
        return self._stance

    def init_state(self, task: str, **kwargs: Any) -> StateSchema:
        from dataclasses import dataclass as _dc

        @_dc
        class _S(StateSchema):
            argument: str = ""

        return _S(task=task, max_steps=3)

    def reduce(self, state: Any, observation: Any, decision: Decision[Any]) -> Any:
        return state

    def build_system_prompt(self, state: Any) -> str | None:
        return (
            f"You are the '{self._stance}' debater. Present your strongest arguments "
            f"for your position on the given topic. Be concise and persuasive."
        )


class _DebateModerator(AgentModule[DebateState, Any, Any]):
    """Moderator agent that orchestrates the debate."""

    name = "debate_moderator"

    def __init__(self, config: DebateConfig, llm: Any = None, **kwargs: Any):
        self._config = config
        super().__init__(llm=llm, **kwargs)

    def init_state(self, task: str, **kwargs: Any) -> DebateState:
        return DebateState(
            task=task,
            max_steps=self._config.moderator_max_steps,
        )

    def build_system_prompt(self, state: DebateState) -> str | None:
        debaters = ", ".join(self._config.debaters)
        return (
            f"You are the debate moderator. The debaters are: {debaters}.\n"
            f"Round: {state.current_round}/{self._config.rounds}\n"
            f"Arguments so far: {len(state.arguments)}\n"
            f"After all rounds, deliver a balanced verdict."
        )

    def reduce(
        self,
        state: DebateState,
        observation: Any,
        decision: Decision[Any],
    ) -> DebateState:
        if decision.actions:
            for action in decision.actions:
                tool_name = getattr(action, "name", None) or (
                    action.get("name") if isinstance(action, dict) else None
                )
                if tool_name and "delegate_to_" in tool_name:
                    state.current_round += 1
                    result = {}
                    if isinstance(observation, dict):
                        results = observation.get("action_results", [])
                        if results:
                            result = results[0] if isinstance(results[0], dict) else {}
                    state.arguments.append({
                        "debater": tool_name.replace("delegate_to_", ""),
                        "round": state.current_round,
                        "argument": str(result),
                    })
                elif tool_name == "done":
                    summary = ""
                    if isinstance(observation, dict):
                        results = observation.get("action_results", [])
                        if results:
                            r = results[0]
                            summary = r.get("summary", str(r)) if isinstance(r, dict) else str(r)
                    state.verdict = summary
                    state.set_stop("final", state.verdict)
        return state

    def should_stop(self, state: DebateState) -> bool:
        return bool(state.verdict) and state.current_round >= self._config.rounds


def build_debate_system(
    config: DebateConfig,
) -> tuple[_DebateModerator, Any]:
    """Build a debate multi-agent system.

    Returns:
        (moderator_agent, agent_registry) tuple.
    """
    from ...core.agent_spec import AgentRegistry, AgentSpec, ContextStrategy

    agent_registry = AgentRegistry()

    # Register debater agents
    for debater_name in config.debaters:
        debater = _DebaterAgent(stance=debater_name, llm=config.llm)
        spec = AgentSpec(
            name=debater_name,
            description=f"Debater arguing the '{debater_name}' position",
            agent=debater,
            context_strategy=ContextStrategy.ISOLATED,
            max_steps_override=config.debater_max_steps,
        )
        agent_registry.register(spec)

    # Build moderator
    moderator = _DebateModerator(config, llm=config.llm)

    # Register delegation tools on moderator
    if hasattr(moderator, "tool_registry") and moderator.tool_registry is not None:
        for delegate_tool in agent_registry.get_delegate_tools():
            moderator.tool_registry.register(delegate_tool)

    return moderator, agent_registry


__all__ = ["DebateConfig", "build_debate_system"]
