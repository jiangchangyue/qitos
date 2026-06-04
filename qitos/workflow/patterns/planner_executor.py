"""Planner-Executor pattern as a DAG schema.

Structure:
  Start → AgentNode(planner) → AgentNode(executor) → End

The simplest multi-agent pattern: a planner creates a plan,
then an executor carries it out. Linear handoff.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from qitos_dag.schema import EdgeSchema, NodeSchema, WorkflowSchema


@dataclass
class PlannerExecutorDagConfig:
    """Configuration for the planner-executor DAG pattern."""

    planner_name: str = "planner"
    executor_name: str = "executor"
    planner_max_steps: int = 5
    executor_max_steps: int = 10
    planner_task_template: str = "Create an execution plan for: {task}"
    executor_task_template: str = "Execute the following plan: {{#planner.result#}}"


def build_planner_executor_schema(
    config: Optional[PlannerExecutorDagConfig] = None,
) -> WorkflowSchema:
    """Build a planner-executor pattern as a DAG WorkflowSchema.

    Parameters
    ----------
    config : PlannerExecutorDagConfig, optional
        Pattern configuration.

    Returns
    -------
    WorkflowSchema
        A compiled workflow schema with planner and executor AgentNodes.
    """
    config = config or PlannerExecutorDagConfig()

    schema = WorkflowSchema(
        title="Planner-Executor Pattern",
        description=f"Planner {config.planner_name} → Executor {config.executor_name}",
        nodes=[
            NodeSchema(id="start", type="start"),
            NodeSchema(
                id="planner",
                type="agent",
                title=f"Planner: {config.planner_name}",
                data={
                    "agent_name": config.planner_name,
                    "max_steps": config.planner_max_steps,
                    "task_template": config.planner_task_template,
                },
            ),
            NodeSchema(
                id="executor",
                type="agent",
                title=f"Executor: {config.executor_name}",
                data={
                    "agent_name": config.executor_name,
                    "max_steps": config.executor_max_steps,
                    "task_template": config.executor_task_template,
                },
            ),
            NodeSchema(id="end", type="end"),
        ],
        edges=[
            EdgeSchema(source="start", target="planner"),
            EdgeSchema(source="planner", target="executor"),
            EdgeSchema(source="executor", target="end"),
        ],
    )

    return schema
