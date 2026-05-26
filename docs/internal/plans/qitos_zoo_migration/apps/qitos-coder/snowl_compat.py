"""Snowl compatibility adapter for qitos_coder.

Provides the adapter interface for running qitos_coder under the
Snowl evaluation framework, including agent construction,
environment requirements, and trajectory serialization.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Snowl agent factory
# ---------------------------------------------------------------------------

REQUIRED_TOOLS: List[str] = ["shell", "file_read", "file_write"]
REQUIRED_ENV: Dict[str, Any] = {
    "type": "host",
    "capabilities": ["filesystem", "command"],
}


def create_snowl_agent(
    *,
    model: Optional[str] = None,
    max_steps: int = 50,
    permission_mode: str = "default",
    **kwargs: Any,
) -> Any:
    """Create a qitos_coder agent compatible with Snowl evaluation.

    Parameters
    ----------
    model : str | None
        Model identifier. Falls back to family preset resolution.
    max_steps : int
        Maximum steps per evaluation run.
    permission_mode : str
        Permission mode: default, plan, acceptEdits, bypassPermissions, auto.
    **kwargs
        Additional arguments forwarded to the agent constructor.

    Returns
    -------
    ClaudeCodeAgent
        A configured agent instance.
    """
    from .claude_code.agent import ClaudeCodeAgent

    return ClaudeCodeAgent(
        model=model,
        max_steps=max_steps,
        permission_mode=permission_mode,
        **kwargs,
    )


def serialize_run(result: Any) -> Dict[str, Any]:
    """Serialize an EngineResult to Snowl-compatible JSON.

    Parameters
    ----------
    result : EngineResult
        Result from running the coder agent.

    Returns
    -------
    dict
        Snowl-compatible trajectory data.
    """
    from qitos.engine.run_state import RunState

    state = RunState.from_engine_result(result, agent_name="qitos_coder")
    raw = state.to_json(pretty=False)
    import json
    return json.loads(raw)


def deserialize_run(raw: str) -> Any:
    """Deserialize a Snowl trajectory back to a RunState.

    Parameters
    ----------
    raw : str
        JSON string from Snowl storage.

    Returns
    -------
    RunState
        Restored run state.
    """
    from qitos.engine.run_state import RunState

    return RunState.from_json(raw)


__all__ = [
    "create_snowl_agent",
    "serialize_run",
    "deserialize_run",
    "REQUIRED_TOOLS",
    "REQUIRED_ENV",
]
