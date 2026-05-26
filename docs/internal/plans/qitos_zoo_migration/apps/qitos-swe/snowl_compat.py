"""Snowl compatibility adapter for qitos_swe."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

REQUIRED_TOOLS: List[str] = ["shell", "file_read", "file_write", "file_edit"]
REQUIRED_ENV: Dict[str, Any] = {
    "type": "repo",
    "capabilities": ["filesystem", "command"],
}


def create_snowl_agent(
    *,
    model: Optional[str] = None,
    max_steps: int = 25,
    **kwargs: Any,
) -> Any:
    """Create a qitos_swe agent for Snowl evaluation."""
    from .agent import QitOSSWEAgent
    from qitos.models.openai_compatible import OpenAICompatibleModel

    api_key = kwargs.get("api_key", "")
    base_url = kwargs.get(
        "base_url",
        "https://api.siliconflow.cn/v1/",
    )
    model_name = model or "Qwen/Qwen3-8B"

    llm = OpenAICompatibleModel(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
    )
    return QitOSSWEAgent(llm=llm, max_steps=max_steps, **kwargs)


def serialize_run(result: Any) -> Dict[str, Any]:
    """Serialize an EngineResult to Snowl-compatible JSON."""
    from qitos.engine.run_state import RunState
    import json

    state = RunState.from_engine_result(result, agent_name="qitos_swe")
    return json.loads(state.to_json(pretty=False))


def deserialize_run(raw: str) -> Any:
    """Deserialize a Snowl trajectory back to a RunState."""
    from qitos.engine.run_state import RunState
    return RunState.from_json(raw)


__all__ = [
    "create_snowl_agent",
    "serialize_run",
    "deserialize_run",
    "REQUIRED_TOOLS",
    "REQUIRED_ENV",
]
