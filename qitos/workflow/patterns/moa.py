"""Mixture-of-Agents (MoA) pattern as a DAG schema.

Structure:
  Start → ParallelNode with one branch per proposer AgentNode
  → AgentNode(aggregator) → End

The ParallelNode runs all proposers concurrently, and the aggregator
synthesizes their proposals into a final answer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from qitos_dag.schema import EdgeSchema, NodeSchema, WorkflowSchema


@dataclass
class MoADagConfig:
    """Configuration for the MoA DAG pattern."""

    proposers: List[str] = field(default_factory=lambda: ["analyst_a", "analyst_b", "analyst_c"])
    aggregator_name: str = "aggregator"
    proposer_max_steps: int = 5
    aggregator_max_steps: int = 10
    task_template: str = "Analyze and provide your perspective on: {task}"


def build_moa_schema(config: Optional[MoADagConfig] = None) -> WorkflowSchema:
    """Build a Mixture-of-Agents pattern as a DAG WorkflowSchema.

    Parameters
    ----------
    config : MoADagConfig, optional
        Pattern configuration. Defaults to 3 proposers + 1 aggregator.

    Returns
    -------
    WorkflowSchema
        A compiled workflow schema with ParallelNode for proposers
        and an aggregator AgentNode after parallel.
    """
    config = config or MoADagConfig()

    # Build parallel branches — one per proposer
    branches = []
    for proposer_name in config.proposers:
        branch_id = proposer_name
        branches.append({
            "branch_id": branch_id,
            "child_schema": {
                "nodes": [
                    {"id": f"{branch_id}_start", "type": "start"},
                    {
                        "id": f"{branch_id}_proposer",
                        "type": "agent",
                        "title": f"Proposer: {proposer_name}",
                        "data": {
                            "agent_name": proposer_name,
                            "max_steps": config.proposer_max_steps,
                            "task_template": config.task_template,
                        },
                    },
                    {"id": f"{branch_id}_end", "type": "end"},
                ],
                "edges": [
                    {"source": f"{branch_id}_start", "target": f"{branch_id}_proposer"},
                    {"source": f"{branch_id}_proposer", "target": f"{branch_id}_end"},
                ],
            },
        })

    schema = WorkflowSchema(
        title="MoA Pattern",
        description=f"Mixture of {len(config.proposers)} proposers with aggregator",
        nodes=[
            NodeSchema(id="start", type="start"),
            NodeSchema(
                id="proposers",
                type="parallel",
                title="Parallel Proposers",
                data={"branches": branches},
            ),
            NodeSchema(
                id="aggregator",
                type="agent",
                title=f"Aggregator: {config.aggregator_name}",
                data={
                    "agent_name": config.aggregator_name,
                    "max_steps": config.aggregator_max_steps,
                    "task_template": "Synthesize the following proposals into a coherent answer: {{#proposers.results#}}",
                },
            ),
            NodeSchema(id="end", type="end"),
        ],
        edges=[
            EdgeSchema(source="start", target="proposers"),
            EdgeSchema(source="proposers", target="aggregator"),
            EdgeSchema(source="aggregator", target="end"),
        ],
    )

    return schema
