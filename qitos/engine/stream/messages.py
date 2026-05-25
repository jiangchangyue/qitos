"""MessagesTransformer — intercept LLM token stream events."""

from __future__ import annotations

from typing import Optional

from ..events import EngineEvent, EngineEventType
from .transformer import StreamTransformer, TransformerOutput


class MessagesTransformer(StreamTransformer):
    """Extract LLM message events from the engine stream.

    Emits a TransformerOutput with ``type="messages"`` for:
    - STEP_STREAM events (token-level chunks)
    - DECIDE events with ``stage="end"`` (complete response)
    """

    output_type = "messages"

    def __init__(self) -> None:
        self._buffer: list[str] = []

    def transform(self, event: EngineEvent) -> Optional[TransformerOutput]:
        if event.event_type == EngineEventType.STEP_STREAM:
            # Token-level chunk
            text = event.payload.get("text", event.payload.get("delta", ""))
            if text:
                self._buffer.append(str(text))
            return TransformerOutput(
                type=self.output_type,
                value={"chunk": text, "step_id": event.step_id},
                step_id=event.step_id,
                metadata={"streaming": True},
            )

        if (
            event.event_type == EngineEventType.DECIDE
            and event.payload.get("stage") == "end"
        ):
            # Complete LLM response
            full_text = "".join(self._buffer)
            self._buffer.clear()
            return TransformerOutput(
                type=self.output_type,
                value={
                    "role": "assistant",
                    "content": full_text,
                    "step_id": event.step_id,
                },
                step_id=event.step_id,
                metadata={"streaming": False},
            )

        return None


__all__ = ["MessagesTransformer"]
