"""Human-in-the-loop node — pause for human input."""

from __future__ import annotations

from typing import Any, Dict

from qitos_dag.node import NodeCategory, NodeConfig, WorkflowNode, register_node_type
from qitos_dag.variable_pool import VariablePool


@register_node_type
class HumanInputNode(WorkflowNode):
    """Pause the workflow and wait for human input.

    In a CLI context, this prompts the user for input.
    In a web context, this would render a form.

    Config data:
        prompt: str — the question/prompt to show the user
        input_type: str — "text" | "choice" | "confirmation"
        choices: list[str] — options for "choice" type
        output_key: str — name for the output (default "response")
    """

    node_type = "human-input"
    category = NodeCategory.EXECUTABLE

    async def run(self, inputs: Dict[str, Any], pool: VariablePool) -> Dict[str, Any]:
        prompt = pool.resolve_template(self.config.data.get("prompt", "Please provide input:"))
        input_type = self.config.data.get("input_type", "text")
        choices = self.config.data.get("choices", [])
        output_key = self.config.data.get("output_key", "response")

        if input_type == "confirmation":
            response = input(f"{prompt} [y/n]: ").strip().lower()
            return {output_key: response in ("y", "yes", "true")}

        if input_type == "choice" and choices:
            print(f"\n{prompt}")
            for i, choice in enumerate(choices):
                print(f"  [{i + 1}] {choice}")
            idx = input("Select: ").strip()
            try:
                selected = choices[int(idx) - 1]
            except (ValueError, IndexError):
                selected = idx
            return {output_key: selected}

        # Default: text input
        response = input(f"{prompt} ")
        return {output_key: response}
