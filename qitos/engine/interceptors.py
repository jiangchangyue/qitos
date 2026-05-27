"""Built-in tool interceptors for QitOS Engine."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..core.action import Action, ActionResult
from ..core.interceptor import InterceptorContext, ToolInterceptor
from .states import RuntimeEvent, RuntimePhase


class DelegateEventInterceptor(ToolInterceptor):
    """Emits DELEGATE_START/DELEGATE_END RuntimeEvents when delegate tools are called.

    Register this interceptor when an AgentRegistry is provided so that
    delegate tool calls appear as first-class events in EngineResult.events.
    """

    def __init__(self, event_sink: Optional[List[RuntimeEvent]] = None) -> None:
        self._event_sink = event_sink

    def _is_delegate_tool(self, tool_name: str) -> bool:
        return tool_name.startswith("delegate_to_")

    def _emit(self, phase: RuntimePhase, context: InterceptorContext, payload: Dict[str, Any]) -> None:
        if self._event_sink is None:
            return
        event = RuntimeEvent(
            step_id=context.step_id,
            phase=phase,
            payload=payload,
        )
        self._event_sink.append(event)

    def before_execute(self, action: Action, context: InterceptorContext) -> Action:
        if self._is_delegate_tool(context.tool_name):
            agent_name = context.tool_name[len("delegate_to_"):]
            self._emit(RuntimePhase.DELEGATE_START, context, {
                "agent": agent_name,
                "task": context.tool_args.get("task", ""),
            })
        return action

    def after_execute(
        self, action: Action, result: ActionResult, context: InterceptorContext
    ) -> ActionResult:
        if self._is_delegate_tool(context.tool_name):
            agent_name = context.tool_name[len("delegate_to_"):]
            result_data = result.data if hasattr(result, "data") else {}
            if isinstance(result_data, dict):
                status = result_data.get("status", "unknown")
            else:
                status = "unknown"
            self._emit(RuntimePhase.DELEGATE_END, context, {
                "agent": agent_name,
                "status": status,
            })
        return result


__all__ = ["DelegateEventInterceptor"]
