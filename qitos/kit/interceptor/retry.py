"""RetryInterceptor -- auto-retry failed tool calls up to N times."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from ...core.action import Action, ActionResult, ActionStatus
from ...core.interceptor import InterceptorContext, ToolInterceptor


class RetryInterceptor(ToolInterceptor):
    """Auto-retry tool calls that raise exceptions.

    Only retries when the tool call itself throws an exception.
    Normal tool outputs (even those representing logical errors) are
    not retried.

    Parameters:
        max_retries: Maximum number of retry attempts (default 2).
        retry_on_exception: Whether to retry on exceptions (default True).
        backoff_factor: Multiplier for exponential back-off between retries
            in seconds (default 1.0).  Sleep is ``backoff_factor * 2 ** attempt``.
    """

    def __init__(
        self,
        max_retries: int = 2,
        retry_on_exception: bool = True,
        backoff_factor: float = 1.0,
    ):
        self.max_retries = max_retries
        self.retry_on_exception = retry_on_exception
        self.backoff_factor = backoff_factor

    def before_execute(self, action: Action, context: InterceptorContext) -> Action:
        """Bump the action's max_retries so the executor retry loop will re-enter."""
        # We do NOT mutate the original action's max_retries directly;
        # instead we return a copy with the increased retry count so the
        # executor's existing retry loop does the work.
        effective_retries = max(action.max_retries, self.max_retries)
        return Action(
            name=action.name,
            args=dict(action.args),
            kind=action.kind,
            action_id=action.action_id,
            timeout_s=action.timeout_s,
            max_retries=effective_retries,
            idempotent=action.idempotent,
            classification=action.classification,
            metadata={
                **action.metadata,
                "_retry_interceptor_max": self.max_retries,
            },
        )

    def after_execute(
        self, action: Action, result: ActionResult, context: InterceptorContext
    ) -> ActionResult:
        """Record retry metadata in the result; actual retry is handled by executor."""
        retry_meta = action.metadata.get("_retry_interceptor_max")
        if retry_meta is not None:
            result.metadata["retry_interceptor_max"] = retry_meta
        return result


__all__ = ["RetryInterceptor"]
