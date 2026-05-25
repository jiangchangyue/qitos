"""Interrupt / Resume mechanism for Engine execution.

Borrowed from LangGraph's interrupt() design:
- references/langgraph/libs/langgraph/langgraph/types.py (lines 801-924)
- Re-execution model: when a step with interrupt() is resumed,
  the step re-runs from the start and interrupt() returns the resume value.
- Ordered interrupt matching via counter.
- OpenAI Agents tool approval (needs_approval):
  references/openai-agents-python/src/agents/tool.py
  references/openai-agents-python/src/agents/run.py (interruption handling)
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..checkpoint.store import CheckpointId


# ---------------------------------------------------------------------------
# Context variables — scoped per async task / thread
# ---------------------------------------------------------------------------

_interrupt_counter: contextvars.ContextVar[int] = contextvars.ContextVar(
    "_interrupt_counter", default=0
)
_resume_values: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    "_resume_values", default={}
)


# ---------------------------------------------------------------------------
# EngineInterrupt exception
# ---------------------------------------------------------------------------

@dataclass
class EngineInterrupt(Exception):
    """Raised by :func:`interrupt` on first invocation.

    Carries enough information for the Engine to save a checkpoint
    and report the interrupt back to the caller.
    """

    value: Any = None
    """The value surfaced to the client (e.g. a question for the human)."""

    interrupt_id: str = ""
    """Ordered identifier within the step (e.g. ``"int_1"``, ``"int_2"``)."""

    checkpoint_id: Optional[CheckpointId] = None
    """Set by Engine after saving the checkpoint."""

    def __post_init__(self) -> None:
        super().__init__(str(self.value))


# ---------------------------------------------------------------------------
# InterruptInfo — surfaced to the caller via StepResult
# ---------------------------------------------------------------------------

@dataclass
class InterruptInfo:
    """Information about a pending interrupt, returned in StepResult."""

    interrupt_id: str
    checkpoint_id: CheckpointId
    value: Any


# ---------------------------------------------------------------------------
# interrupt() function
# ---------------------------------------------------------------------------

def interrupt(value: Any = None) -> Any:
    """Pause execution and wait for a resume value.

    On **first call** within a step:
    - Saves a checkpoint (if checkpoint_store is configured).
    - Raises :class:`EngineInterrupt`, halting the step.

    On **resume** (step re-executes):
    - Returns the resume value provided by the caller.

    Multiple ``interrupt()`` calls in a single step are matched
    by their execution order.

    Args:
        value: The value to surface to the client when the engine
            is interrupted (e.g. a question, a prompt for approval).

    Returns:
        The resume value on re-execution.

    Raises:
        EngineInterrupt: On first invocation within the step.
    """
    counter = _interrupt_counter.get() + 1
    _interrupt_counter.set(counter)
    interrupt_id = f"int_{counter}"

    # Check if we have a resume value for this interrupt
    resume_vals = _resume_values.get()
    if interrupt_id in resume_vals:
        return resume_vals[interrupt_id]

    # No resume value — raise interrupt
    raise EngineInterrupt(value=value, interrupt_id=interrupt_id)


# ---------------------------------------------------------------------------
# Internal helpers (used by Engine)
# ---------------------------------------------------------------------------

def _reset_interrupt_context() -> None:
    """Reset interrupt context at the start of each step."""
    _interrupt_counter.set(0)


def _set_resume_values(values: Dict[str, Any]) -> None:
    """Set resume values before re-executing an interrupted step."""
    _resume_values.set(values)


def _clear_resume_values() -> None:
    """Clear resume values after they've been consumed."""
    _resume_values.set({})


__all__ = [
    "interrupt",
    "EngineInterrupt",
    "InterruptInfo",
    "_reset_interrupt_context",
    "_set_resume_values",
    "_clear_resume_values",
]
