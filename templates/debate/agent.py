"""Debate multi-agent template — two agents argue for/against a proposition.

Provides configuration and registry setup for a debate pattern where:
- A proponent argues in favor of a proposition
- An opponent argues against it
- A judge evaluates the debate and delivers a verdict

Usage:
    from templates.debate.agent import DebateConfig, build_debate_registry
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from qitos.core.agent_spec import AgentSpec, ContextStrategy, HandoffContext, AgentRegistry
from qitos.core.shared_memory import InMemorySharedMemory, SharedMemoryManager


@dataclass
class DebateConfig:
    """Configuration for a debate multi-agent system."""

    proposition: str = ""
    max_rounds: int = 3
    pro_agent_name: str = "proponent"
    con_agent_name: str = "opponent"
    judge_agent_name: str = "judge"
    context_strategy: str = "summary"
    shared_memory_fields: List[str] = field(default_factory=lambda: ["arguments", "round"])


def build_debate_registry(config: DebateConfig) -> tuple[AgentRegistry, SharedMemoryManager]:
    """Build an AgentRegistry and SharedMemoryManager for the debate pattern.

    The caller must register concrete AgentModule instances with the
    returned specs before running the engine.

    Returns:
        (registry, shared_memory_manager)
    """
    shared_memory = SharedMemoryManager(InMemorySharedMemory())
    registry = AgentRegistry()

    registry.register(AgentSpec(
        name=config.pro_agent_name,
        description=f"Argues in favor of: {config.proposition}",
        agent=None,  # Caller must provide a concrete agent
        context_strategy=ContextStrategy.SUMMARY,
        handoff_context=HandoffContext(
            strategy=ContextStrategy.SUMMARY,
            shared_state_fields=config.shared_memory_fields,
        ),
    ))

    registry.register(AgentSpec(
        name=config.con_agent_name,
        description=f"Argues against: {config.proposition}",
        agent=None,
        context_strategy=ContextStrategy.SUMMARY,
        handoff_context=HandoffContext(
            strategy=ContextStrategy.SUMMARY,
            shared_state_fields=config.shared_memory_fields,
        ),
    ))

    registry.register(AgentSpec(
        name=config.judge_agent_name,
        description="Evaluates the debate and delivers a verdict",
        agent=None,
        context_strategy=ContextStrategy.FULL,
        handoff_context=HandoffContext(
            strategy=ContextStrategy.FULL,
            shared_state_fields=config.shared_memory_fields + ["verdict"],
        ),
    ))

    return registry, shared_memory
