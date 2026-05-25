"""Console trace processor: logs trace/span events via Python logging."""

from __future__ import annotations

import logging
from typing import Optional

from .models import Span, Trace
from .processor import TraceProcessor


class ConsoleTraceProcessor(TraceProcessor):
    """Trace processor that writes human-readable events to a Python logger.

    Format::

        [QitOS Trace] {trace_id} | {span_type} | {span_id} | {duration_ms}ms | {summary}
    """

    def __init__(
        self,
        level: int = logging.INFO,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._level = level
        self._logger = logger or logging.getLogger("qitos.tracing.console")

    # -- TraceProcessor interface -------------------------------------------

    def on_trace_start(self, trace: Trace) -> None:
        self._logger.log(
            self._level,
            "[QitOS Trace] %s | trace_start | name=%s",
            trace.trace_id,
            trace.name,
        )

    def on_trace_end(self, trace: Trace) -> None:
        span_count = len(trace._spans)
        self._logger.log(
            self._level,
            "[QitOS Trace] %s | trace_end | spans=%d",
            trace.trace_id,
            span_count,
        )

    def on_span_start(self, span: Span) -> None:
        self._logger.log(
            self._level,
            "[QitOS Trace] %s | %s | %s | start",
            span.trace_id,
            span.data.type,
            span.span_id,
        )

    def on_span_end(self, span: Span) -> None:
        duration_ms = self._duration_ms(span)
        summary = self._summarize(span)
        self._logger.log(
            self._level,
            "[QitOS Trace] %s | %s | %s | %dms | %s",
            span.trace_id,
            span.data.type,
            span.span_id,
            duration_ms,
            summary,
        )

    def shutdown(self) -> None:
        pass

    def force_flush(self) -> None:
        pass

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _duration_ms(span: Span) -> int:
        """Compute the span duration in milliseconds.

        Returns 0 if timing data is missing.
        """
        if span.started_at is None or span.ended_at is None:
            return 0
        try:
            from datetime import datetime, timezone

            start = datetime.fromisoformat(span.started_at)
            end = datetime.fromisoformat(span.ended_at)
            return int((end - start).total_seconds() * 1000)
        except Exception:
            return 0

    @staticmethod
    def _summarize(span: Span) -> str:
        """Create a short human-readable summary from span data."""
        data = span.data
        # Dispatch on data type to produce useful summaries
        if hasattr(data, "name"):
            return str(data.name)
        if hasattr(data, "tool_name"):
            return str(data.tool_name)
        if hasattr(data, "action_name"):
            return str(data.action_name)
        if hasattr(data, "critic_name"):
            return str(data.critic_name)
        if span.error:
            return f"error={span.error}"
        return "ok"
