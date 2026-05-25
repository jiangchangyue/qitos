"""Parameter inference — infer state type, tool list, and model from function signatures."""

from __future__ import annotations

import inspect
from typing import Any, Dict, Optional, get_type_hints


def infer_state_type(func: Any) -> Optional[type]:
    """Infer the state type from a function's ``state`` parameter annotation.

    Returns None if no ``state`` parameter exists or has no annotation.
    """
    try:
        hints = get_type_hints(func)
    except Exception:
        hints = {}
    state_type = hints.get("state")
    if state_type is not None:
        return state_type
    # Fallback to signature inspection
    sig = inspect.signature(func)
    param = sig.parameters.get("state")
    if param is None or param.annotation is inspect.Parameter.empty:
        return None
    ann = param.annotation
    if isinstance(ann, str):
        return None  # Can't resolve forward reference
    return ann


def infer_tool_list(func: Any) -> list[Any]:
    """Infer tool list from a function's ``tools`` parameter.

    Returns empty list if no ``tools`` parameter or no default.
    """
    sig = inspect.signature(func)
    param = sig.parameters.get("tools")
    if param is None:
        return []
    default = param.default
    if default is inspect.Parameter.empty:
        return []
    if isinstance(default, list):
        return default
    return []


def infer_model(func: Any) -> Optional[str]:
    """Infer the model name from a function's ``model`` parameter default.

    Returns None if no ``model`` parameter or no default.
    """
    sig = inspect.signature(func)
    param = sig.parameters.get("model")
    if param is None:
        return None
    default = param.default
    if default is inspect.Parameter.empty:
        return None
    return str(default)


def infer_parameters(func: Any) -> Dict[str, Any]:
    """Infer all configurable parameters from a function signature.

    Returns a dict with keys: state_type, tools, model, and any
    other keyword parameters with defaults.
    """
    result: Dict[str, Any] = {}

    state_type = infer_state_type(func)
    if state_type is not None:
        result["state_type"] = state_type

    tools = infer_tool_list(func)
    if tools:
        result["tools"] = tools

    model = infer_model(func)
    if model is not None:
        result["model"] = model

    # Collect other keyword parameters with defaults
    sig = inspect.signature(func)
    for name, param in sig.parameters.items():
        if name in ("state", "tools", "model"):
            continue
        if param.default is not inspect.Parameter.empty:
            result[name] = param.default

    return result


__all__ = [
    "infer_state_type",
    "infer_tool_list",
    "infer_model",
    "infer_parameters",
]
