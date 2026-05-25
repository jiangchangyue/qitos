"""E2E test utility tools — @function_tool decorated for real tool calling."""
from __future__ import annotations

from typing import Any, Dict, List

from qitos.core.function_tool_decorator import function_tool


# ---------------------------------------------------------------------------
# Calculator tools
# ---------------------------------------------------------------------------


class CalculatorToolSet:
    """Simple calculator tools for E2E testing."""

    name = "calculator"
    version = "1"

    def setup(self, context: Dict[str, Any]) -> None:
        pass

    def teardown(self, context: Dict[str, Any]) -> None:
        pass

    @function_tool(
        name="add",
        description="Add two numbers together",
        read_only=True,
    )
    def add(self, a: float, b: float) -> Dict[str, Any]:
        return {"result": a + b, "operation": "add", "inputs": [a, b]}

    @function_tool(
        name="multiply",
        description="Multiply two numbers together",
        read_only=True,
    )
    def multiply(self, a: float, b: float) -> Dict[str, Any]:
        return {"result": a * b, "operation": "multiply", "inputs": [a, b]}

    @function_tool(
        name="subtract",
        description="Subtract b from a",
        read_only=True,
    )
    def subtract(self, a: float, b: float) -> Dict[str, Any]:
        return {"result": a - b, "operation": "subtract", "inputs": [a, b]}

    @function_tool(
        name="dangerous_divide",
        description="Divide a by b (requires approval because division can cause errors)",
        needs_approval=True,
    )
    def divide(self, a: float, b: float) -> Dict[str, Any]:
        if b == 0:
            return {"result": "error: division by zero", "operation": "divide"}
        return {"result": a / b, "operation": "divide", "inputs": [a, b]}

    def tools(self) -> List[Any]:
        return [self.add, self.multiply, self.subtract, self.divide]


# ---------------------------------------------------------------------------
# String tools
# ---------------------------------------------------------------------------


class StringToolSet:
    """String operation tools for E2E testing."""

    name = "string_utils"
    version = "1"

    def setup(self, context: Dict[str, Any]) -> None:
        pass

    def teardown(self, context: Dict[str, Any]) -> None:
        pass

    @function_tool(
        name="count_chars",
        description="Count the number of characters in a string",
        read_only=True,
    )
    def count_chars(self, text: str) -> Dict[str, Any]:
        return {"result": len(text), "operation": "count_chars", "input_length": len(text)}

    @function_tool(
        name="reverse_string",
        description="Reverse a string",
        read_only=True,
    )
    def reverse_string(self, text: str) -> Dict[str, Any]:
        return {"result": text[::-1], "operation": "reverse_string"}

    @function_tool(
        name="uppercase",
        description="Convert string to uppercase",
        read_only=True,
    )
    def uppercase(self, text: str) -> Dict[str, Any]:
        return {"result": text.upper(), "operation": "uppercase"}

    def tools(self) -> List[Any]:
        return [self.count_chars, self.reverse_string, self.uppercase]
