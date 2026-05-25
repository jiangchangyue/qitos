"""Tool approval request types for QitOS engine."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ToolApprovalItem:
    """Structured approval request for a tool call that requires human review."""

    tool_name: str
    tool_args: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    tool_spec: Optional[Any] = None  # Optional ToolSpec reference
