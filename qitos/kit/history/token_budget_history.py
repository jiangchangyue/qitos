"""History implementation with token-budget-aware summarization."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from qitos.core.history import History, HistoryMessage


class TokenBudgetSummaryHistory(History):
    def __init__(
        self,
        *,
        llm: Any | None = None,
        max_tokens: int = 16000,
        keep_last: int = 8,
        hard_window: int = 64,
    ):
        self.llm = llm
        self.max_tokens = int(max_tokens)
        self.keep_last = int(keep_last)
        self.hard_window = int(hard_window)
        self._messages: List[HistoryMessage] = []

    def append(self, message: HistoryMessage) -> None:
        self._messages.append(message)
        self.evict()

    def retrieve(
        self,
        query: Optional[Dict[str, Any]] = None,
        state: Any = None,
        observation: Any = None,
    ) -> List[HistoryMessage]:
        query = query or {}
        items = self._filter_messages(query)
        max_items = int(query.get("max_items", len(items) if items else self.hard_window))
        if max_items > 0:
            items = items[-max_items:]

        budget = int(query.get("max_tokens") or self.max_tokens)
        pending = str(query.get("pending_content") or "")
        if budget <= 0:
            return items
        if self._estimate_tokens(items) + self._estimate_text_tokens(pending) <= budget:
            return items

        if len(items) <= self.keep_last:
            return items[-self.keep_last :]

        recent = items[-self.keep_last :]
        old = items[: -self.keep_last]
        if not old:
            return recent
        summary = self._summarize_messages(old)
        summary_message = HistoryMessage(
            role="system",
            content=summary,
            step_id=old[-1].step_id,
            metadata={"source": "token_budget_summary", "summary": True},
        )
        return [summary_message, *recent]

    def summarize(self, max_items: int = 5) -> str:
        items = self.retrieve(query={"max_items": max_items})
        return "\n".join(f"[{m.step_id}] {m.role}: {m.content[:120]}" for m in items)

    def evict(self) -> int:
        if self.hard_window <= 0 or len(self._messages) <= self.hard_window:
            return 0
        removed = len(self._messages) - self.hard_window
        self._messages = self._messages[-self.hard_window :]
        return removed

    def reset(self, run_id: Optional[str] = None) -> None:
        self._messages = []

    def _filter_messages(self, query: Dict[str, Any]) -> List[HistoryMessage]:
        items = list(self._messages)
        roles = query.get("roles")
        step_min = query.get("step_min")
        step_max = query.get("step_max")
        if roles:
            role_set = {str(x) for x in roles}
            items = [m for m in items if m.role in role_set]
        if step_min is not None:
            items = [m for m in items if m.step_id >= int(step_min)]
        if step_max is not None:
            items = [m for m in items if m.step_id <= int(step_max)]
        return items

    def _summarize_messages(self, messages: List[HistoryMessage]) -> str:
        prompt = self._summary_prompt(messages)
        if self.llm is not None:
            try:
                response = self.llm(
                    [
                        {
                            "role": "system",
                            "content": "Summarize prior agent interaction for continuity. Preserve discoveries, failures, and pending work. Keep it concise and factual.",
                        },
                        {"role": "user", "content": prompt},
                    ]
                )
                summary = str(response or "").strip()
                if summary:
                    return summary
            except Exception:
                pass
        return self._heuristic_summary(messages)

    def _summary_prompt(self, messages: List[HistoryMessage]) -> str:
        body = "\n".join(f"[{m.step_id}] {m.role}: {m.content}" for m in messages)
        return (
            "Summarize the following interaction history for a continuation model call. "
            "Keep key findings, mistakes, tool results, and remaining intent.\n\n"
            f"{body}"
        )

    def _heuristic_summary(self, messages: List[HistoryMessage]) -> str:
        lines = [f"[{m.step_id}] {m.role}: {m.content[:160]}" for m in messages[-12:]]
        return "Summary of earlier interaction:\n" + "\n".join(lines)

    def _estimate_tokens(self, messages: List[HistoryMessage]) -> int:
        return sum(self._estimate_text_tokens(m.content) for m in messages)

    def _estimate_text_tokens(self, text: Any) -> int:
        s = str(text or "")
        if not s:
            return 0
        return max(1, len(s) // 4)


__all__ = ["TokenBudgetSummaryHistory"]
