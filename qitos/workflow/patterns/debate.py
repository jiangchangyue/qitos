"""Debate pattern as a DAG schema.

Structure:
  Start → LoopNode(rounds) containing:
    AgentNode(proponent) → AgentNode(opponent) [alternating per iteration]
  → AgentNode(moderator) → End

The LoopNode carries arguments across rounds via conversation variables.
The moderator produces a verdict after all rounds complete.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from qitos_dag.schema import EdgeSchema, NodeSchema, WorkflowSchema


@dataclass
class DebateDagConfig:
    """Configuration for the debate DAG pattern."""

    debaters: List[str] = field(default_factory=lambda: ["proponent", "opponent"])
    rounds: int = 3
    moderator_name: str = "moderator"
    debater_max_steps: int = 3
    moderator_max_steps: int = 10
    task_template: str = "Debate the following topic: {task}"


def build_debate_schema(config: Optional[DebateDagConfig] = None) -> WorkflowSchema:
    """Build a debate pattern as a DAG WorkflowSchema.

    Parameters
    ----------
    config : DebateDagConfig, optional
        Pattern configuration. Defaults to 2 debaters, 3 rounds.

    Returns
    -------
    WorkflowSchema
        A compiled workflow schema with LoopNode for debate rounds
        and a moderator AgentNode after the loop.
    """
    config = config or DebateDagConfig()

    # Build child schema for each debate round
    debater_nodes = []
    debater_edges = []
    prev_id = "round_start"

    debater_nodes.append(NodeSchema(id="round_start", type="start"))

    for i, debater_name in enumerate(config.debaters):
        node_id = f"debater_{i}_{debater_name}"
        debater_nodes.append(NodeSchema(
            id=node_id,
            type="agent",
            title=f"Debater: {debater_name}",
            data={
                "agent_name": debater_name,
                "max_steps": config.debater_max_steps,
                "task_template": f"Present your argument as {debater_name} on: {{{{#conversation.debate_topic#}}}}",
            },
        ))
        debater_edges.append(EdgeSchema(source=prev_id, target=node_id))
        prev_id = node_id

    debater_nodes.append(NodeSchema(id="round_end", type="end"))
    debater_edges.append(EdgeSchema(source=prev_id, target="round_end"))

    child_schema_data = {
        "nodes": [{"id": n.id, "type": n.type, "title": n.title or "", "data": n.data} for n in debater_nodes],
        "edges": [{"source": e.source, "target": e.target} for e in debater_edges],
    }

    schema = WorkflowSchema(
        title="Debate Pattern",
        description=f"{len(config.debaters)}-debater debate with {config.rounds} rounds",
        nodes=[
            NodeSchema(id="start", type="start"),
            NodeSchema(
                id="debate_rounds",
                type="loop",
                title="Debate Rounds",
                data={
                    "mode": "by_count",
                    "count": config.rounds,
                    "child_schema": child_schema_data,
                    "loop_variables": {"debate_topic": ""},
                },
            ),
            NodeSchema(
                id="moderator",
                type="agent",
                title=f"Moderator: {config.moderator_name}",
                data={
                    "agent_name": config.moderator_name,
                    "max_steps": config.moderator_max_steps,
                    "task_template": "Review all arguments and provide a verdict on: {{#conversation.debate_topic#}}",
                },
            ),
            NodeSchema(id="end", type="end"),
        ],
        edges=[
            EdgeSchema(source="start", target="debate_rounds"),
            EdgeSchema(source="debate_rounds", target="moderator"),
            EdgeSchema(source="moderator", target="end"),
        ],
    )

    return schema
