"""QitOS Workflow Integration Layer.

This module integrates qitos-dag with QitOS, providing workflow nodes
that leverage QitOS's AgentModule, Engine, ToolRegistry, and qita
tracing infrastructure.

Bidirectional DAG-Engine bridge:
- DAG → Engine: AgentNode runs Engine with full injection (shared_memory,
  tracing_provider, agent_registry, hooks)
- Engine → DAG: WorkflowTool triggers DAG workflows from agent tools
- Shared: VariablePool, SharedMemory, Tracing, Events bridged across
"""

from .factory import QitosNodeFactory
from .runner import WorkflowRunner
from .adapter import SharedMemoryAdapter
from .event_bridge import EngineToDagHook, DagToEngineLayer
from .registry import WorkflowRegistry, WorkflowSpec

__all__ = [
    "QitosNodeFactory",
    "WorkflowRunner",
    "SharedMemoryAdapter",
    "EngineToDagHook",
    "DagToEngineLayer",
    "WorkflowRegistry",
    "WorkflowSpec",
]
