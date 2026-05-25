"""Mixture-of-Agents (MoA) pattern — parallel proposals, Aggregator synthesis.

Usage::

    from qitos.kit.patterns import build_moa_system, MoAConfig

    config = MoAConfig(
        proposers=["analyst_a", "analyst_b", "analyst_c"],
        llm=my_llm,
    )
    aggregator, registry = build_moa_system(config)
    result = aggregator.run(task="Evaluate this system design")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Any, Dict, List, Optional

from ...core.agent_module import AgentModule
from ...core.channel import Append
from ...core.decision import Decision
from ...core.state import StateSchema


@dataclass
class MoAConfig:
    """Configuration for the Mixture-of-Agents pattern."""

    proposers: List[str] = field(default_factory=lambda: ["analyst_a", "analyst_b", "analyst_c"])
    aggregator_name: str = "aggregator"
    proposer_max_steps: int = 5
    aggregator_max_steps: int = 10
    llm: Any = None
    workspace_root: str = "."


@dataclass
class MoAState(StateSchema):
    """State for the MoA aggregator."""

    proposals: Annotated[List[Dict[str, Any]], Append] = field(default_factory=list)  # noqa: F821
    synthesis: str = ""


class _ProposerAgent(AgentModule):
    """A single proposer agent."""

    def __init__(self, name: str, llm: Any = None, **kwargs: Any):
        self._proposer_name = name
        super().__init__(llm=llm, **kwargs)

    @property
    def name(self) -> str:  # type: ignore[override]
        return self._proposer_name

    def init_state(self, task: str, **kwargs: Any) -> StateSchema:
        from dataclasses import dataclass as _dc

        @_dc
        class _S(StateSchema):
            proposal: str = ""

        return _S(task=task, max_steps=5)

    def reduce(self, state: Any, observation: Any, decision: Decision[Any]) -> Any:
        return state

    def build_system_prompt(self, state: Any) -> str | None:
        return (
            f"You are '{self._proposer_name}', an independent analyst. "
            f"Provide your unique perspective and analysis on the given topic. "
            f"Be thorough and creative."
        )


class _MoAAggregator(AgentModule[MoAState, Any, Any]):
    """Aggregator agent that synthesizes proposals."""

    name = "moa_aggregator"

    def __init__(self, config: MoAConfig, llm: Any = None, **kwargs: Any):
        self._config = config
        super().__init__(llm=llm, **kwargs)

    def init_state(self, task: str, **kwargs: Any) -> MoAState:
        return MoAState(
            task=task,
            max_steps=self._config.aggregator_max_steps,
        )

    def build_system_prompt(self, state: MoAState) -> str | None:
        proposals_count = len(state.proposals)
        proposers = ", ".join(self._config.proposers)
        return (
            f"You are the aggregator. Proposers: {proposers}.\n"
            f"Proposals collected: {proposals_count}\n"
            f"Synthesize the best insights from all proposals into a coherent answer."
        )

    def reduce(
        self,
        state: MoAState,
        observation: Any,
        decision: Decision[Any],
    ) -> MoAState:
        if decision.actions:
            for action in decision.actions:
                tool_name = getattr(action, "name", None) or (
                    action.get("name") if isinstance(action, dict) else None
                )
                if tool_name and "delegate_to_" in tool_name:
                    result = {}
                    if isinstance(observation, dict):
                        results = observation.get("action_results", [])
                        if results:
                            result = results[0] if isinstance(results[0], dict) else {}
                    state.proposals.append({
                        "proposer": tool_name.replace("delegate_to_", ""),
                        "proposal": str(result),
                    })
                elif tool_name == "done":
                    summary = ""
                    if isinstance(observation, dict):
                        results = observation.get("action_results", [])
                        if results:
                            r = results[0]
                            summary = r.get("summary", str(r)) if isinstance(r, dict) else str(r)
                    state.synthesis = summary
                    state.set_stop("final", state.synthesis)
        return state

    def should_stop(self, state: MoAState) -> bool:
        return bool(state.synthesis) and len(state.proposals) >= len(self._config.proposers)


def build_moa_system(
    config: MoAConfig,
) -> tuple[_MoAAggregator, Any]:
    """Build a Mixture-of-Agents multi-agent system.

    Returns:
        (aggregator_agent, agent_registry) tuple.
    """
    from ...core.agent_spec import AgentRegistry, AgentSpec, ContextStrategy

    agent_registry = AgentRegistry()

    # Register proposer agents
    for proposer_name in config.proposers:
        proposer = _ProposerAgent(name=proposer_name, llm=config.llm)
        spec = AgentSpec(
            name=proposer_name,
            description=f"Independent analyst '{proposer_name}'",
            agent=proposer,
            context_strategy=ContextStrategy.ISOLATED,
            max_steps_override=config.proposer_max_steps,
        )
        agent_registry.register(spec)

    # Build aggregator
    aggregator = _MoAAggregator(config, llm=config.llm)

    # Register delegation tools on aggregator
    if hasattr(aggregator, "tool_registry") and aggregator.tool_registry is not None:
        for delegate_tool in agent_registry.get_delegate_tools():
            aggregator.tool_registry.register(delegate_tool)

    return aggregator, agent_registry


__all__ = ["MoAConfig", "build_moa_system"]
