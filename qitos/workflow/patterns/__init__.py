"""DAG-based multi-agent pattern builders.

Each pattern returns a WorkflowSchema that can be:
- Passed to WorkflowRunner.run() directly
- Used as child_schema inside SubWorkflowNode
- Registered in WorkflowRegistry

These complement (not replace) the Engine-based patterns in
qitos.kit.patterns.* — both approaches coexist.
"""

from .debate import build_debate_schema, DebateDagConfig
from .moa import build_moa_schema, MoADagConfig
from .manager_worker import build_manager_worker_schema, ManagerWorkerDagConfig
from .planner_executor import build_planner_executor_schema, PlannerExecutorDagConfig

__all__ = [
    "build_debate_schema", "DebateDagConfig",
    "build_moa_schema", "MoADagConfig",
    "build_manager_worker_schema", "ManagerWorkerDagConfig",
    "build_planner_executor_schema", "PlannerExecutorDagConfig",
]
