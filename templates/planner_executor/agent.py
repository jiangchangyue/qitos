"""Planner-Executor multi-agent template — a planner decomposes, an executor carries out.

Provides configuration and registry setup for a planner-executor pattern where:
- A planner breaks down a task into ordered subtasks
- An executor carries out each subtask in isolation
- The planner reviews results and adjusts the plan

Usage:
    from templates.planner_executor.agent import PlannerExecutorConfig, build_planner_executor_registry
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from qitos.core.agent_spec import AgentSpec, ContextStrategy, HandoffContext, AgentRegistry
from qitos.core.shared_memory import InMemorySharedMemory, SharedMemoryManager


@dataclass
class PlannerExecutorConfig:
    """Configuration for a planner-executor multi-agent system."""

    planner_name: str = "planner"
    executor_name: str = "executor"
    max_subtasks: int = 5
    context_strategy: str = "summary"
    shared_memory_fields: List[str] = field(default_factory=lambda: ["plan", "step_result", "overall_result"])


def build_planner_executor_registry(config: PlannerExecutorConfig) -> tuple[AgentRegistry, SharedMemoryManager]:
    """Build an AgentRegistry and SharedMemoryManager for the planner-executor pattern.

    Key design:
    - Planner uses FULL context — sees the complete plan and all results
    - Executor uses ISOLATED context — only receives the current subtask

    The caller must register concrete AgentModule instances with the
    returned specs before running the engine.

    Returns:
        (registry, shared_memory_manager)
    """
    shared_memory = SharedMemoryManager(InMemorySharedMemory())
    registry = AgentRegistry()

    registry.register(AgentSpec(
        name=config.planner_name,
        description="Decomposes tasks into subtasks and tracks progress",
        agent=None,  # Caller must provide a concrete agent
        context_strategy=ContextStrategy.FULL,
        handoff_context=HandoffContext(
            strategy=ContextStrategy.FULL,
            shared_state_fields=config.shared_memory_fields,
        ),
    ))

    registry.register(AgentSpec(
        name=config.executor_name,
        description="Executes individual subtasks and returns results",
        agent=None,
        context_strategy=ContextStrategy.ISOLATED,
        handoff_context=HandoffContext(
            strategy=ContextStrategy.ISOLATED,
            shared_state_fields=config.shared_memory_fields,
        ),
    ))

    return registry, shared_memory
