"""Agent specification and registry for multi-agent delegation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Generic, List, Optional, TypeVar

if TYPE_CHECKING:
    from .agent_module import AgentModule


SourceStateT = TypeVar("SourceStateT")
TargetStateT = TypeVar("TargetStateT")


class ContextStrategy(str, Enum):
    """Controls what context a sub-agent receives from its parent."""

    FULL = "full"
    SUMMARY = "summary"
    ISOLATED = "isolated"


@dataclass
class HandoffContext:
    """Context package passed between agents during delegation."""

    strategy: ContextStrategy = ContextStrategy.SUMMARY
    payload: Dict[str, Any] = field(default_factory=dict)
    shared_state_fields: List[str] = field(default_factory=list)
    max_history_rounds: Optional[int] = None


@dataclass
class StateAdapter(ABC, Generic[SourceStateT, TargetStateT]):
    """Converts state between agents with different StateT types during handoff."""

    @abstractmethod
    def adapt(self, source: SourceStateT) -> TargetStateT:
        """Convert source state to the target state type."""


@dataclass
class AgentSpec:
    """Describes an agent available for delegation."""

    name: str
    description: str
    agent: AgentModule
    context_strategy: ContextStrategy = ContextStrategy.SUMMARY
    max_steps_override: Optional[int] = None
    shared_env: bool = True
    state_adapter: Optional[StateAdapter] = None
    handoff_context: Optional[HandoffContext] = None
    shared_memory: Optional[Any] = None  # SharedMemory instance
    model_override: Optional[str] = None
    tools_override: Optional[Any] = None  # ToolRegistry instance

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("AgentSpec.name must be non-empty")


class AgentRegistry:
    """Manages agents available for delegation within a run."""

    def __init__(self) -> None:
        self._specs: Dict[str, AgentSpec] = {}

    def register(self, spec: AgentSpec) -> None:
        if spec.name in self._specs:
            raise ValueError(f"Agent '{spec.name}' is already registered")
        self._specs[spec.name] = spec

    def resolve(self, name: str) -> AgentSpec:
        if name not in self._specs:
            raise KeyError(f"Agent '{name}' not found in registry")
        return self._specs[name]

    def list_available(self) -> List[AgentSpec]:
        return list(self._specs.values())

    def get_delegate_tools(self) -> List[Any]:
        """Return a DelegateTool for each registered agent spec.

        Imports DelegateTool lazily to avoid circular imports.
        """
        from ..kit.tool.delegate import DelegateTool

        return [DelegateTool(spec=spec, agent_registry=self) for spec in self._specs.values()]

    def get_fanout_tool(self, max_workers: int = 4, per_task_timeout: float = 120.0) -> Any:
        """Return a FanOutTool backed by this registry.

        Imports FanOutTool lazily to avoid circular imports.
        """
        from ..kit.tool.fanout import FanOutTool

        return FanOutTool(agent_registry=self, max_workers=max_workers, per_task_timeout=per_task_timeout)

    def get_handoff_tools(self) -> List[Any]:
        """Return a HandoffTool for each registered agent spec.

        HandoffTools enable Decision-mode agent switching in the Engine loop.
        Imports lazily to avoid circular imports.
        """
        from ..kit.tool.handoff_tool import HandoffTool

        return [
            HandoffTool(
                target_name=spec.name,
                target_description=spec.description,
            )
            for spec in self._specs.values()
        ]

    def validate_topology(self) -> List[str]:
        """Validate the handoff graph and return a list of warnings.

        Checks:
        - handoff_targets reference agents that exist in the registry
        - Detects potential cycles (A→B→A)
        - Detects isolated agents (no inbound handoff targets from other agents)

        Returns
        -------
        list[str]
            Warning messages. Empty list means no issues found.
        """
        warnings: List[str] = []
        agent_names = set(self._specs.keys())

        # Build adjacency from handoff_targets attributes
        adjacency: Dict[str, List[str]] = {}
        for name, spec in self._specs.items():
            targets = getattr(spec.agent, "handoff_targets", None) or []
            adjacency[name] = targets
            for t in targets:
                if t not in agent_names:
                    warnings.append(
                        f"Agent '{name}' references unknown handoff target '{t}'"
                    )

        # Detect cycles via DFS
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {name: WHITE for name in agent_names}

        def dfs(node: str, path: List[str]) -> None:
            color[node] = GRAY
            path.append(node)
            for neighbor in adjacency.get(node, []):
                if neighbor not in color:
                    continue
                if color[neighbor] == GRAY:
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    warnings.append(
                        f"Handoff cycle detected: {' → '.join(cycle)}"
                    )
                elif color[neighbor] == WHITE:
                    dfs(neighbor, path)
            path.pop()
            color[node] = BLACK

        for name in agent_names:
            if color[name] == WHITE:
                dfs(name, [])

        # Detect isolated agents (no inbound handoff from other registered agents)
        inbound_targets: Dict[str, int] = {name: 0 for name in agent_names}
        for name, targets in adjacency.items():
            for t in targets:
                if t in inbound_targets:
                    inbound_targets[t] += 1
        for name, count in inbound_targets.items():
            if count == 0 and len(agent_names) > 1:
                # Not necessarily a problem, just informational
                warnings.append(
                    f"Agent '{name}' has no inbound handoff targets "
                    f"(other agents never hand off to it)"
                )

        return warnings
