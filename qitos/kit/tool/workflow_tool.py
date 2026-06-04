"""WorkflowTool — invoke a DAG workflow from within an Engine loop.

Enables an agent to delegate complex multi-step orchestration
(conditional branching, loops, parallel execution) to the DAG
engine, while the agent loop stays in observe-decide-act-reduce.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from qitos.core.tool import BaseTool, ToolSpec


class WorkflowTool(BaseTool):
    """Tool that triggers a DAG workflow from within an Engine loop.

    The agent can invoke this tool to run a pre-registered workflow
    schema with conditional branching, loops, and parallel execution —
    capabilities that are natural in DAG but awkward in the linear
    Engine loop.
    """

    def __init__(
        self,
        runner: Any,
        spec: Any,
        shared_memory: Any = None,
    ) -> None:
        self.runner = runner
        self.workflow_spec = spec
        self.shared_memory = shared_memory

        tool_spec = ToolSpec(
            name=f"run_workflow_{spec.name}",
            description=f"Run the '{spec.name}' workflow: {spec.description}",
            parameters={
                "inputs": {
                    "type": "object",
                    "description": "Input values for the workflow",
                },
            },
            required=[],
        )
        super().__init__(spec=tool_spec)

    def execute(
        self, args: Dict[str, Any], runtime_context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute the workflow via WorkflowRunner.run_sync()."""
        from qitos.workflow.event_bridge import DagToEngineLayer
        from qitos.workflow.runner import WorkflowRunner

        # Extract inputs
        workflow_inputs = args.get("inputs", {})
        workflow_inputs.update(self.workflow_spec.default_inputs)

        # Bridge SharedMemory from parent context
        sm = self.shared_memory
        if sm is None and runtime_context:
            sm = runtime_context.get("shared_memory")

        # Update runner's shared_memory if available
        if sm is not None and hasattr(self.runner, "shared_memory"):
            self.runner.shared_memory = sm
            if hasattr(self.runner, "factory"):
                self.runner.factory.shared_memory = sm

        # Run workflow synchronously
        schema = self.workflow_spec.schema
        result = self.runner.run_sync(schema, inputs=workflow_inputs)

        # Build return value
        if result.succeeded:
            return {
                "status": "succeeded",
                "node_results": result.node_results,
                "elapsed_ms": result.elapsed_ms,
            }
        else:
            return {
                "status": "failed",
                "error": result.error,
                "node_results": result.node_results,
            }
