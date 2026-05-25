"""Snowl compatibility adapter for qitos_researcher."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

REQUIRED_TOOLS: List[str] = ["http_get", "extract_web_text", "file_read", "file_write"]
REQUIRED_ENV: Dict[str, Any] = {
    "type": "host",
    "capabilities": ["filesystem", "network"],
}


def create_snowl_agent(
    *,
    model: Optional[str] = None,
    max_steps: int = 20,
    **kwargs: Any,
) -> Any:
    """Create a qitos_researcher agent for Snowl evaluation."""
    from .agent import QitOSResearcher
    from qitos.models.openai_compatible import OpenAICompatibleModel

    api_key = kwargs.get("api_key", "")
    base_url = kwargs.get(
        "base_url",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    model_name = model or "qwen-plus"

    llm = OpenAICompatibleModel(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
    )
    return QitOSResearcher(llm=llm, max_steps=max_steps, **kwargs)


def serialize_run(result: Any) -> Dict[str, Any]:
    """Serialize an EngineResult to Snowl-compatible JSON."""
    from qitos.engine.run_state import RunState
    import json

    state = RunState.from_engine_result(result, agent_name="qitos_researcher")
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
