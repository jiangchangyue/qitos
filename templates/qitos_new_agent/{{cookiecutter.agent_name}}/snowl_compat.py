"""Snowl compatibility adapter for {{cookiecutter.agent_name}}."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

REQUIRED_TOOLS: List[str] = []
REQUIRED_ENV: Dict[str, Any] = {}


def create_snowl_agent(**kwargs: Any) -> Any:
    """Create the {{cookiecutter.agent_name}} agent for Snowl evaluation."""
    from .src.agent import {{cookiecutter.agent_name | pascalcase}}Agent
    return {{cookiecutter.agent_name | pascalcase}}Agent(**kwargs)


def serialize_run(result: Any) -> Dict[str, Any]:
    """Serialize EngineResult to Snowl JSON."""
    from qitos.engine.run_state import RunState
    import json

    state = RunState.from_engine_result(result, agent_name="{{cookiecutter.agent_name}}")
    return json.loads(state.to_json(pretty=False))


def deserialize_run(raw: str) -> Any:
    """Deserialize Snowl JSON back to RunState."""
    from qitos.engine.run_state import RunState
    return RunState.from_json(raw)
