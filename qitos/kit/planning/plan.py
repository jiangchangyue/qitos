"""Planning helpers for AgentModule state management."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def parse_numbered_plan(text: str) -> List[str]:
    if not text:
        return []
    lines = text.splitlines()
    items: List[str] = []
    for line in lines:
        s = line.strip()
        m = re.match(r"^(\d+)[\.)]\s*(.+)$", s)
        if m:
            items.append(m.group(2).strip())
    return items


class NumberedPlanBuilder:
    """Small reusable helper for LLM-based numbered plan generation."""

    def __init__(self, system_prompt: str = "Return a numbered plan only."):
        self.system_prompt = system_prompt

    def build(self, llm: Any, prompt: str, extra_messages: Optional[List[Dict[str, str]]] = None) -> List[str]:
        messages: List[Dict[str, str]] = [{"role": "system", "content": self.system_prompt}]
        if extra_messages:
            messages.extend(extra_messages)
        messages.append({"role": "user", "content": prompt})
        raw = llm(messages)
        return parse_numbered_plan(str(raw))


class PlanCursor:
    """Operate plan/cursor fields on arbitrary state objects safely."""

    def __init__(self, plan_field: str = "plan", cursor_field: str = "plan_cursor"):
        self.plan_field = plan_field
        self.cursor_field = cursor_field

    def init(self, state: Any, plan: List[str]) -> None:
        setattr(state, self.plan_field, list(plan))
        setattr(state, self.cursor_field, 0)

    def current(self, state: Any) -> Optional[str]:
        plan = list(getattr(state, self.plan_field, []))
        cursor = int(getattr(state, self.cursor_field, 0))
        if cursor < 0 or cursor >= len(plan):
            return None
        return plan[cursor]

    def advance(self, state: Any) -> None:
        cursor = int(getattr(state, self.cursor_field, 0))
        setattr(state, self.cursor_field, cursor + 1)

    def done(self, state: Any) -> bool:
        plan = list(getattr(state, self.plan_field, []))
        cursor = int(getattr(state, self.cursor_field, 0))
        return cursor >= len(plan)


__all__ = ["parse_numbered_plan", "NumberedPlanBuilder", "PlanCursor"]
