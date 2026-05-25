"""Trace processor protocol and fan-out implementation."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import List, Optional

from .models import Trace, Span

logger = logging.getLogger(__name__)


class TraceProcessor(ABC):
    """Interface for processing trace and span lifecycle events.

    Implementations may log, persist, or transmit trace data.  All
    methods are called by the TracingProvider when spans and traces
    start and finish.
    """

    @abstractmethod
    def on_trace_start(self, trace: Trace) -> None:
        """Called when a trace begins."""

    @abstractmethod
    def on_trace_end(self, trace: Trace) -> None:
        """Called when a trace finishes (all spans are closed)."""

    @abstractmethod
    def on_span_start(self, span: Span) -> None:
        """Called when a span starts."""

    @abstractmethod
    def on_span_end(self, span: Span) -> None:
        """Called when a span finishes."""

    def shutdown(self) -> None:
        """Perform any cleanup.  Default is a no-op."""

    def force_flush(self) -> None:
        """Force-flush any buffered data.  Default is a no-op."""


class SynchronousMultiTraceProcessor(TraceProcessor):
    """Fan-out processor that delegates to a list of child processors.

    Each child processor is called in order.  Errors in one processor
    are caught and logged so that a failing processor cannot break the
    fan-out chain.
    """

    def __init__(self, processors: Optional[List[TraceProcessor]] = None) -> None:
        self._processors: List[TraceProcessor] = list(processors or [])

    # -- mutation -----------------------------------------------------------

    def add_processor(self, processor: TraceProcessor) -> None:
        self._processors.append(processor)

    def remove_processor(self, processor: TraceProcessor) -> None:
        try:
            self._processors.remove(processor)
        except ValueError:
            pass

    @property
    def processors(self) -> List[TraceProcessor]:
        return list(self._processors)

    # -- TraceProcessor interface -------------------------------------------

    def on_trace_start(self, trace: Trace) -> None:
        for proc in self._processors:
            try:
                proc.on_trace_start(trace)
            except Exception:
                logger.exception("Error in %s.on_trace_start", type(proc).__name__)

    def on_trace_end(self, trace: Trace) -> None:
        for proc in self._processors:
            try:
                proc.on_trace_end(trace)
            except Exception:
                logger.exception("Error in %s.on_trace_end", type(proc).__name__)

    def on_span_start(self, span: Span) -> None:
        for proc in self._processors:
            try:
                proc.on_span_start(span)
            except Exception:
                logger.exception("Error in %s.on_span_start", type(proc).__name__)

    def on_span_end(self, span: Span) -> None:
        for proc in self._processors:
            try:
                proc.on_span_end(span)
            except Exception:
                logger.exception("Error in %s.on_span_end", type(proc).__name__)

    def shutdown(self) -> None:
        for proc in self._processors:
            try:
                proc.shutdown()
            except Exception:
                logger.exception("Error in %s.shutdown", type(proc).__name__)

    def force_flush(self) -> None:
        for proc in self._processors:
            try:
                proc.force_flush()
            except Exception:
                logger.exception("Error in %s.force_flush", type(proc).__name__)


class NoOpTraceProcessor(TraceProcessor):
    """Processor that discards everything.  Used when tracing is disabled."""

    def on_trace_start(self, trace: Trace) -> None:
        pass

    def on_trace_end(self, trace: Trace) -> None:
        pass

    def on_span_start(self, span: Span) -> None:
        pass

    def on_span_end(self, span: Span) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def force_flush(self) -> None:
        pass
