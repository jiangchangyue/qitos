"""Reusable planning state helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class PlanState:
    """Optional plan state block for planner-executor agents."""

    steps: List[str] = field(default_factory=list)
    cursor: int = 0
    status: str = "idle"

    def validate(self) -> None:
        if self.cursor < 0:
            raise ValueError("PlanState.cursor must be >= 0")
        if self.cursor > len(self.steps):
            raise ValueError("PlanState.cursor cannot exceed number of steps")
        if self.status not in {"idle", "executing", "completed"}:
            raise ValueError("PlanState.status must be idle/executing/completed")
