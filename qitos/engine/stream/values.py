"""ValuesTransformer — extract full state after each step."""

from __future__ import annotations

from typing import Optional

from ..events import EngineEvent, EngineEventType
from .transformer import StreamTransformer, TransformerOutput


class ValuesTransformer(StreamTransformer):
    """Extract the full state after each step completes.

    Emits a TransformerOutput with ``type="values"`` and
    ``value=state`` after each STEP_END event.
    """

    output_type = "values"

    def __init__(self) -> None:
        self._last_state: Optional[object] = None

    def transform(self, event: EngineEvent) -> Optional[TransformerOutput]:
        if event.event_type != EngineEventType.STEP_END:
            return None

        # The payload may contain the state
        state = event.payload.get("state")
        if state is None:
            # Try to extract from the engine via the event
            state = self._last_state

        if state is not None:
            self._last_state = state

        return TransformerOutput(
            type=self.output_type,
            value=state,
            step_id=event.step_id,
        )


__all__ = ["ValuesTransformer"]
