"""Tool Node — invoke a QitOS tool from a workflow."""

from __future__ import annotations

from typing import Any, Dict, Optional

from qitos_dag.node import NodeCategory, NodeConfig, WorkflowNode, register_node_type
from qitos_dag.variable_pool import VariablePool


@register_node_type
class ToolNode(WorkflowNode):
    """Invoke a QitOS tool by name.

    Config data:
        tool_name: str — the registered tool name
        tool_args: dict — arguments to pass to the tool (supports template refs)
    """

    node_type = "tool"
    category = NodeCategory.EXECUTABLE

    def validate_config(self) -> None:
        if not self.config.data.get("tool_name"):
            raise ValueError(f"ToolNode '{self.id}': missing tool_name")

    async def run(self, inputs: Dict[str, Any], pool: VariablePool) -> Dict[str, Any]:
        tool_name = self.config.data["tool_name"]
        tool_args_template = self.config.data.get("tool_args", {})

        # Resolve template references in args
        resolved_args = {}
        for key, value in tool_args_template.items():
            if isinstance(value, str):
                resolved_args[key] = pool.resolve_template(value)
            else:
                resolved_args[key] = value

        # Merge with inputs
        resolved_args.update(inputs)

        # Get tool registry from injected context
        tool_registry = self.config.data.get("_tool_registry")
        if tool_registry is None:
            return {"error": f"No ToolRegistry available for tool '{tool_name}'"}

        try:
            result = tool_registry.call(tool_name, runtime_context={}, **resolved_args)
            if isinstance(result, dict):
                return result
            return {"output": result}
        except ValueError as exc:
            return {"error": str(exc)}
        except Exception as exc:
            return {"error": str(exc)}
