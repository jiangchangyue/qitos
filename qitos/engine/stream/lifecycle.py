"""LifecycleTransformer — handle interrupt/resume lifecycle events."""

from __future__ import annotations

from typing import Optional

from ..events import EngineEvent, EngineEventType
from .transformer import StreamTransformer, TransformerOutput


class LifecycleTransformer(StreamTransformer):
    """Extract interrupt/resume lifecycle events from the engine stream.

    Emits a TransformerOutput with ``type="lifecycle"`` for:
    - INTERRUPT events
    - RUN_START / RUN_END events
    - ERROR events
    """

    output_type = "lifecycle"

    def __init__(self) -> None:
        self._interrupts: list[dict] = []
        self._errors: list[dict] = []

    def transform(self, event: EngineEvent) -> Optional[TransformerOutput]:
        if event.event_type == EngineEventType.INTERRUPT:
            interrupt_data = {
                "step_id": event.step_id,
                "payload": event.payload,
            }
            self._interrupts.append(interrupt_data)
            return TransformerOutput(
                type=self.output_type,
                value={"event": "interrupt", **interrupt_data},
                step_id=event.step_id,
            )

        if event.event_type == EngineEventType.RUN_START:
            return TransformerOutput(
                type=self.output_type,
                value={"event": "run_start", "task": event.payload.get("task", "")},
                step_id=event.step_id,
            )

        if event.event_type == EngineEventType.RUN_END:
            return TransformerOutput(
                type=self.output_type,
                value={
                    "event": "run_end",
                    "step_count": event.payload.get("step_count", 0),
                    "stop_reason": event.payload.get("stop_reason"),
                },
                step_id=event.step_id,
            )

        if event.event_type == EngineEventType.ERROR:
            error_data = {
                "step_id": event.step_id,
                "error": event.error,
                "payload": event.payload,
            }
            self._errors.append(error_data)
            return TransformerOutput(
                type=self.output_type,
                value={"event": "error", **error_data},
                step_id=event.step_id,
            )

        return None

    @property
    def interrupts(self) -> list[dict]:
        return list(self._interrupts)

    @property
    def errors(self) -> list[dict]:
        return list(self._errors)


__all__ = ["LifecycleTransformer"]
