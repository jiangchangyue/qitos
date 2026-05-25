"""Manager-Worker multi-agent template — a manager delegates tasks to workers.

Provides configuration and registry setup for a manager-worker pattern where:
- A manager decomposes tasks and delegates to workers
- Workers execute subtasks and return results
- The manager aggregates results

Usage:
    from templates.manager_worker.agent import ManagerWorkerConfig, WorkerDef, build_manager_worker_registry
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from qitos.core.agent_spec import AgentSpec, ContextStrategy, HandoffContext, AgentRegistry
from qitos.core.shared_memory import InMemorySharedMemory, SharedMemoryManager


@dataclass
class WorkerDef:
    """Definition of a worker agent."""

    name: str
    description: str
    capabilities: List[str] = field(default_factory=list)


@dataclass
class ManagerWorkerConfig:
    """Configuration for a manager-worker multi-agent system."""

    manager_name: str = "manager"
    workers: List[WorkerDef] = field(default_factory=list)
    context_strategy: str = "summary"
    shared_memory_fields: List[str] = field(default_factory=lambda: ["task", "result"])


def build_manager_worker_registry(config: ManagerWorkerConfig) -> tuple[AgentRegistry, SharedMemoryManager]:
    """Build an AgentRegistry and SharedMemoryManager for the manager-worker pattern.

    The caller must register concrete AgentModule instances with the
    returned specs before running the engine.

    Returns:
        (registry, shared_memory_manager)
    """
    shared_memory = SharedMemoryManager(InMemorySharedMemory())
    registry = AgentRegistry()

    registry.register(AgentSpec(
        name=config.manager_name,
        description="Orchestrates tasks and delegates to workers",
        agent=None,  # Caller must provide a concrete agent
        context_strategy=ContextStrategy.FULL,
    ))

    for worker in config.workers:
        registry.register(AgentSpec(
            name=worker.name,
            description=worker.description,
            agent=None,
            context_strategy=ContextStrategy.SUMMARY,
            handoff_context=HandoffContext(
                strategy=ContextStrategy.SUMMARY,
                shared_state_fields=config.shared_memory_fields,
            ),
        ))

    return registry, shared_memory
