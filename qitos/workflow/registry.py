"""Workflow Registry — named, pre-registered workflow schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from qitos_dag.schema import WorkflowSchema


@dataclass
class WorkflowSpec:
    """Describes a workflow available for invocation from agents."""

    name: str
    description: str
    schema: WorkflowSchema
    default_inputs: Dict[str, Any] = field(default_factory=dict)


class WorkflowRegistry:
    """Manages named workflow schemas for discovery and invocation.

    Analogous to AgentRegistry for agents — agents can discover
    available workflows and invoke them via WorkflowTool.
    """

    def __init__(self) -> None:
        self._specs: Dict[str, WorkflowSpec] = {}

    def register(self, spec: WorkflowSpec) -> None:
        if spec.name in self._specs:
            raise ValueError(f"Workflow '{spec.name}' is already registered")
        self._specs[spec.name] = spec

    def resolve(self, name: str) -> WorkflowSpec:
        if name not in self._specs:
            raise KeyError(f"Workflow '{name}' not found in registry")
        return self._specs[name]

    def list_available(self) -> List[WorkflowSpec]:
        return list(self._specs.values())

    def get_workflow_tools(
        self, runner: Any, shared_memory: Any = None
    ) -> List[Any]:
        """Return a WorkflowTool for each registered workflow spec.

        Parameters
        ----------
        runner : WorkflowRunner
            The runner to use for executing workflows.
        shared_memory : Any
            Optional SharedMemory to bridge into the workflow.
        """
        from ..kit.tool.workflow_tool import WorkflowTool

        return [
            WorkflowTool(runner=runner, spec=spec, shared_memory=shared_memory)
            for spec in self._specs.values()
        ]
