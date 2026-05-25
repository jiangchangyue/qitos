"""LoggingInterceptor -- log tool calls to a logger or callback."""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from ...core.action import Action, ActionResult, ActionStatus
from ...core.interceptor import InterceptorContext, ToolInterceptor

_DEFAULT_LOGGER = logging.getLogger("qitos.interceptor.logging")


class LoggingInterceptor(ToolInterceptor):
    """Log tool calls to a Python logger or a custom callback.

    Parameters:
        logger: A ``logging.Logger`` instance.  Falls back to
            ``logging.getLogger("qitos.interceptor.logging")`` if not provided.
        callback: An optional callable ``callback(event: str, **kwargs)`` that
            receives ``"before"`` / ``"after"`` events with details.
        log_args: Whether to include tool arguments in the log (default True).
        log_result: Whether to include the tool result in the after-log
            (default False — results can be large).
    """

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        callback: Optional[Callable[..., None]] = None,
        log_args: bool = True,
        log_result: bool = False,
    ):
        self._logger = logger or _DEFAULT_LOGGER
        self.callback = callback
        self.log_args = log_args
        self.log_result = log_result

    def before_execute(self, action: Action, context: InterceptorContext) -> Action:
        """Log before tool execution."""
        parts = [f"[before] tool={action.name}"]
        if self.log_args:
            parts.append(f"args={action.args}")
        if context.step_id is not None:
            parts.append(f"step={context.step_id}")
        if context.run_id:
            parts.append(f"run={context.run_id}")
        message = " ".join(parts)
        self._logger.info(message)

        if self.callback is not None:
            try:
                self.callback(
                    "before",
                    tool_name=action.name,
                    tool_args=action.args if self.log_args else None,
                    step_id=context.step_id,
                    run_id=context.run_id,
                )
            except Exception:
                pass  # Don't let callback errors disrupt execution

        return action

    def after_execute(
        self, action: Action, result: ActionResult, context: InterceptorContext
    ) -> ActionResult:
        """Log after tool execution."""
        parts = [f"[after] tool={action.name} status={result.status.value}"]
        if result.latency_ms is not None:
            parts.append(f"latency={result.latency_ms:.1f}ms")
        if self.log_result and result.output is not None:
            parts.append(f"result={result.output}")
        if context.step_id is not None:
            parts.append(f"step={context.step_id}")
        message = " ".join(parts)
        self._logger.info(message)

        if self.callback is not None:
            try:
                self.callback(
                    "after",
                    tool_name=action.name,
                    status=result.status.value,
                    latency_ms=result.latency_ms,
                    result=result.output if self.log_result else None,
                    step_id=context.step_id,
                    run_id=context.run_id,
                )
            except Exception:
                pass

        return result


__all__ = ["LoggingInterceptor"]
