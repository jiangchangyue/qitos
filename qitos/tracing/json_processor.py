"""JSON file trace processor: persists trace data to JSON / JSONL files."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from .models import Span, Trace
from .processor import TraceProcessor


class JsonFileTraceProcessor(TraceProcessor):
    """Writes trace data to JSON files on disk.

    Modes:
    - **Batch** (default): on ``on_trace_end()``, writes a single
      ``trace_{trace_id}.json`` containing the full trace and all spans.
    - **Streaming** (``streaming=True``): each span is appended as a
      JSONL line to ``trace_{trace_id}.jsonl`` as soon as it finishes,
      and the final trace metadata is written on ``on_trace_end()``.

    Parameters
    ----------
    output_dir:
        Directory where trace files are written.  Created on
        initialisation if it does not exist.
    streaming:
        If ``True``, write each span as a JSONL line immediately on
        ``on_span_end()`` instead of batching everything at the end.
    indent:
        JSON indentation for the batch mode file.  ``None`` produces
        compact output.
    """

    def __init__(
        self,
        output_dir: str = ".traces",
        streaming: bool = False,
        indent: Optional[int] = 2,
    ) -> None:
        self._output_dir = output_dir
        self._streaming = streaming
        self._indent = indent
        os.makedirs(self._output_dir, exist_ok=True)

        # For streaming mode, we track which traces are open and their
        # accumulated span dicts.
        self._streaming_spans: Dict[str, List[Dict[str, Any]]] = {}

    # -- TraceProcessor interface -------------------------------------------

    def on_trace_start(self, trace: Trace) -> None:
        if self._streaming:
            self._streaming_spans[trace.trace_id] = []

    def on_trace_end(self, trace: Trace) -> None:
        if self._streaming:
            # Write a final metadata footer to the JSONL file
            spans = self._streaming_spans.pop(trace.trace_id, [])
            trace_meta = {
                "trace_id": trace.trace_id,
                "name": trace.name,
                "group_id": trace.group_id,
                "metadata": trace.metadata,
                "span_count": len(spans),
                "type": "trace_end",
            }
            path = os.path.join(
                self._output_dir, f"trace_{trace.trace_id}.jsonl"
            )
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(trace_meta, ensure_ascii=False))
                f.write("\n")
        else:
            # Batch mode: write everything as a single JSON file
            path = os.path.join(
                self._output_dir, f"trace_{trace.trace_id}.json"
            )
            payload = trace.export()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=self._indent)

    def on_span_start(self, span: Span) -> None:
        # No action needed in either mode
        pass

    def on_span_end(self, span: Span) -> None:
        if self._streaming:
            span_dict = span.export()
            span_dict["type"] = "span"
            path = os.path.join(
                self._output_dir, f"trace_{span.trace_id}.jsonl"
            )
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(span_dict, ensure_ascii=False))
                f.write("\n")
            # Also accumulate for the count in on_trace_end
            if span.trace_id in self._streaming_spans:
                self._streaming_spans[span.trace_id].append(span_dict)

    def shutdown(self) -> None:
        pass

    def force_flush(self) -> None:
        pass
