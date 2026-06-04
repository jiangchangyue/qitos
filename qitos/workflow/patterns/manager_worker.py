"""Manager-Worker pattern as a DAG schema.

Structure:
  Start → AgentNode(manager) → IterationNode for worker dispatch → End

The manager decides subtasks, and workers execute them in parallel.
The IterationNode iterates over the manager's task list.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from qitos_dag.schema import EdgeSchema, NodeSchema, WorkflowSchema


@dataclass
class ManagerWorkerDagConfig:
    """Configuration for the manager-worker DAG pattern."""

    manager_name: str = "manager"
    worker_name: str = "worker"
    manager_max_steps: int = 12
    worker_max_steps: int = 5
    max_workers: int = 4
    manager_task_template: str = "Break down this task and delegate subtasks: {task}"
    worker_task_template: str = "Execute this subtask: {{#iteration.item#}}"


def build_manager_worker_schema(
    config: Optional[ManagerWorkerDagConfig] = None,
) -> WorkflowSchema:
    """Build a manager-worker pattern as a DAG WorkflowSchema.

    Parameters
    ----------
    config : ManagerWorkerDagConfig, optional
        Pattern configuration.

    Returns
    -------
    WorkflowSchema
        A compiled workflow schema with manager and worker AgentNodes.
    """
    config = config or ManagerWorkerDagConfig()

    # Worker child schema for iteration
    worker_child_schema = {
        "nodes": [
            {"id": "iter_start", "type": "start"},
            {
                "id": "worker",
                "type": "agent",
                "title": f"Worker: {config.worker_name}",
                "data": {
                    "agent_name": config.worker_name,
                    "max_steps": config.worker_max_steps,
                    "task_template": config.worker_task_template,
                },
            },
            {"id": "iter_end", "type": "end"},
        ],
        "edges": [
            {"source": "iter_start", "target": "worker"},
            {"source": "worker", "target": "iter_end"},
        ],
    }

    schema = WorkflowSchema(
        title="Manager-Worker Pattern",
        description=f"Manager {config.manager_name} dispatches to worker {config.worker_name}",
        nodes=[
            NodeSchema(id="start", type="start"),
            NodeSchema(
                id="manager",
                type="agent",
                title=f"Manager: {config.manager_name}",
                data={
                    "agent_name": config.manager_name,
                    "max_steps": config.manager_max_steps,
                    "task_template": config.manager_task_template,
                },
            ),
            NodeSchema(
                id="set_tasks",
                type="code",
                title="Parse Task List",
                data={
                    "code": "def main(inputs):\n    result = inputs.get('result', '')\n    tasks = [t.strip() for t in result.split('\\n') if t.strip()]\n    return {'items': tasks[:10]}",
                },
            ),
            NodeSchema(
                id="workers",
                type="iteration",
                title="Worker Dispatch",
                data={
                    "iterator_selector": ["set_tasks", "items"],
                    "child_schema": worker_child_schema,
                },
            ),
            NodeSchema(id="end", type="end"),
        ],
        edges=[
            EdgeSchema(source="start", target="manager"),
            EdgeSchema(source="manager", target="set_tasks"),
            EdgeSchema(source="set_tasks", target="workers"),
            EdgeSchema(source="workers", target="end"),
        ],
    )

    return schema
