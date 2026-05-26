"""Snowl compatibility adapter for qitos_cyber (PentAGI).

Provides the adapter interface for running the PentAGI penetration testing
agent under the Snowl evaluation framework, including CyBench and
CyberGym benchmark configuration.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Snowl agent factory
# ---------------------------------------------------------------------------

REQUIRED_TOOLS: List[str] = [
    "shell",
    "search_network",
    "search_vector_db",
    "pentest_delegate",
    "generate_report",
]
REQUIRED_ENV: Dict[str, Any] = {
    "type": "host",
    "capabilities": ["filesystem", "command", "network"],
}


def create_snowl_agent(
    *,
    model: Optional[str] = None,
    max_steps: int = 200,
    **kwargs: Any,
) -> Any:
    """Create a qitos_cyber (PentAGI) agent for Snowl evaluation.

    Parameters
    ----------
    model : str | None
        Model identifier. Falls back to family preset resolution.
    max_steps : int
        Maximum steps per pentest run.
    **kwargs
        Additional arguments forwarded to the agent constructor.

    Returns
    -------
    Agent
        A configured agent instance.
    """
    from .pentagi.runner import PentAGIRunner

    return PentAGIRunner(
        model=model,
        max_steps=max_steps,
        **kwargs,
    )


def map_results_to_trajectory(result: Any) -> Dict[str, Any]:
    """Map PentAGI results to QitOS TrajectoryEvaluator format.

    Parameters
    ----------
    result : EngineResult
        Result from running the cyber agent.

    Returns
    -------
    dict
        Trajectory data in QitOS evaluation format.
    """
    from qitos.engine.run_state import RunState
    import json

    state = RunState.from_engine_result(result, agent_name="qitos_cyber")
    data = json.loads(state.to_json(pretty=False))

    # Extract PentAGI-specific metrics
    state_obj = getattr(result, "state", None)
    data["eval_metrics"] = {
        "step_count": getattr(result, "step_count", 0),
        "total_tokens": getattr(result, "total_tokens", 0),
        "completed": getattr(state_obj, "final_result", None) is not None,
    }

    return data


def serialize_run(result: Any) -> Dict[str, Any]:
    """Serialize a pentest result to Snowl-compatible JSON.

    Parameters
    ----------
    result : EngineResult
        Result from running the cyber agent.

    Returns
    -------
    dict
        Snowl-compatible trajectory data.
    """
    return map_results_to_trajectory(result)


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
    "map_results_to_trajectory",
    "serialize_run",
    "deserialize_run",
    "REQUIRED_TOOLS",
    "REQUIRED_ENV",
]
