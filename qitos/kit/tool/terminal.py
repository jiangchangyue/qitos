"""Interactive terminal control tool."""

from __future__ import annotations

from typing import Any, Dict, Optional

from qitos.core.tool import BaseTool, ToolPermission, ToolSpec


class SendTerminalKeys(BaseTool):
    """Send raw keystrokes to an interactive terminal session managed by the env.

    Use this tool when the agent is operating a terminal UI or long-lived shell
    session where commands must be typed into the same process over time instead
    of executed as isolated shell commands.
    """

    def __init__(self):
        super().__init__(
            ToolSpec(
                name="send_terminal_keys",
                description="Send raw keystrokes to an interactive terminal session",
                parameters={
                    "keystrokes": {"type": "string"},
                    "duration_sec": {"type": "number"},
                    "block": {"type": "boolean"},
                    "max_timeout_sec": {"type": "number"},
                },
                required=["keystrokes"],
                permissions=ToolPermission(command=True),
                required_ops=["terminal"],
            )
        )

    def execute(
        self, args: Dict[str, Any], runtime_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send raw keystrokes to the active interactive terminal session.

        :param keystrokes: Text or control sequence to send to the terminal.
        :param duration_sec: Minimum amount of time to wait after sending input.
        :param block: Whether the terminal backend should block until the step settles.
        :param max_timeout_sec: Upper bound on backend waiting time.
        :param runtime_context: Optional runtime ops injected by the engine.

        The terminal content itself is not returned by this tool; the env is
        responsible for producing the next terminal observation.
        """
        runtime_context = runtime_context or {}
        keystrokes = str(args.get("keystrokes", ""))
        duration_sec = float(args.get("duration_sec", 1.0))
        block = bool(args.get("block", False))
        max_timeout_sec = float(args.get("max_timeout_sec", 180.0))
        ops = runtime_context.get("ops", {})
        terminal_ops = ops.get("terminal")
        if terminal_ops is None or not hasattr(terminal_ops, "send_keys"):
            return {"status": "error", "error": "terminal ops are not available"}
        result = terminal_ops.send_keys(
            keys=keystrokes,
            min_timeout_sec=float(duration_sec),
            block=bool(block),
            max_timeout_sec=float(max_timeout_sec),
        )
        if isinstance(result, dict):
            return result
        return {"status": "success", "result": result}


__all__ = ["SendTerminalKeys"]
