"""Tests for Handoff context strategies: FullContextFilter, SummaryContextFilter, IsolatedContextFilter."""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from qitos.engine._handoff_runtime import (
    ContextFilter,
    FullContextFilter,
    SummaryContextFilter,
    IsolatedContextFilter,
    get_context_filter,
    HandoffResult,
    compact_handoff_history,
    _HandoffRuntime,
)
from qitos.core.agent_spec import ContextStrategy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_history(n: int, start_role: str = "user") -> list[dict]:
    """Create a simple alternating-role history of n items."""
    roles = ["user", "assistant"]
    return [
        {"role": roles[i % 2], "content": f"msg-{i}"}
        for i in range(n)
    ]


def _make_history_with_system(n: int) -> list[dict]:
    """Create history with a system message at the start."""
    hist = [{"role": "system", "content": "system prompt"}]
    hist.extend(_make_history(n))
    return hist


# ---------------------------------------------------------------------------
# ContextFilter ABC
# ---------------------------------------------------------------------------


class TestContextFilterABC:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            ContextFilter()

    def test_subclass_must_implement_filter_history(self):
        class Incomplete(ContextFilter):
            pass

        with pytest.raises(TypeError):
            Incomplete()


# ---------------------------------------------------------------------------
# FullContextFilter
# ---------------------------------------------------------------------------


class TestFullContextFilter:
    def test_returns_copy_of_history(self):
        original = _make_history(5)
        f = FullContextFilter()
        result = f.filter_history(original)
        assert result == original
        assert result is not original  # must be a copy

    def test_empty_history(self):
        f = FullContextFilter()
        assert f.filter_history([]) == []

    def test_task_param_ignored(self):
        original = _make_history(3)
        f = FullContextFilter()
        result = f.filter_history(original, task="new task")
        assert result == original

    def test_preserves_all_messages(self):
        history = _make_history_with_system(10)
        f = FullContextFilter()
        result = f.filter_history(history)
        assert len(result) == 11


# ---------------------------------------------------------------------------
# SummaryContextFilter
# ---------------------------------------------------------------------------


class TestSummaryContextFilter:
    def test_short_history_unchanged(self):
        history = _make_history(4)  # 4 < 3*2 = 6
        f = SummaryContextFilter(keep_recent_rounds=3)
        result = f.filter_history(history)
        assert len(result) == 4

    def test_long_history_compressed(self):
        history = _make_history(20)
        f = SummaryContextFilter(keep_recent_rounds=3)
        result = f.filter_history(history)
        # max_items = 3*2 = 6 recent items + 1 summary = 7
        assert len(result) == 7

    def test_summary_is_system_message(self):
        history = _make_history(20)
        f = SummaryContextFilter(keep_recent_rounds=3)
        result = f.filter_history(history)
        assert result[0]["role"] == "system"
        assert "summarized" in result[0]["content"].lower()

    def test_recent_messages_preserved(self):
        history = _make_history(20)
        f = SummaryContextFilter(keep_recent_rounds=3)
        result = f.filter_history(history)
        # Last 6 items should be the same
        assert result[-6:] == history[-6:]

    def test_custom_keep_recent_rounds(self):
        history = _make_history(30)
        f = SummaryContextFilter(keep_recent_rounds=5)
        result = f.filter_history(history)
        # max_items = 5*2 = 10 recent + 1 summary = 11
        assert len(result) == 11

    def test_custom_summary_prefix(self):
        history = _make_history(20)
        f = SummaryContextFilter(summary_prefix="[COMPACT] ")
        result = f.filter_history(history)
        assert result[0]["content"].startswith("[COMPACT] ")

    def test_empty_history(self):
        f = SummaryContextFilter()
        assert f.filter_history([]) == []


# ---------------------------------------------------------------------------
# IsolatedContextFilter
# ---------------------------------------------------------------------------


class TestIsolatedContextFilter:
    def test_removes_all_non_system(self):
        history = _make_history_with_system(10)
        f = IsolatedContextFilter()
        result = f.filter_history(history, task="do something")
        # system prompt + task user message
        assert len(result) == 2
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"
        assert result[1]["content"] == "do something"

    def test_no_system_messages_only_task(self):
        history = _make_history(5)
        f = IsolatedContextFilter()
        result = f.filter_history(history, task="new task")
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "new task"

    def test_no_task_no_system(self):
        history = _make_history(5)
        f = IsolatedContextFilter()
        result = f.filter_history(history)
        assert result == []

    def test_multiple_system_messages(self):
        history = [
            {"role": "system", "content": "sys1"},
            {"role": "user", "content": "msg1"},
            {"role": "system", "content": "sys2"},
            {"role": "assistant", "content": "msg2"},
        ]
        f = IsolatedContextFilter()
        result = f.filter_history(history, task="task")
        # 2 system + 1 task
        assert len(result) == 3
        assert result[0]["content"] == "sys1"
        assert result[1]["content"] == "sys2"
        assert result[2]["content"] == "task"

    def test_empty_history_with_task(self):
        f = IsolatedContextFilter()
        result = f.filter_history([], task="task")
        assert len(result) == 1
        assert result[0]["content"] == "task"


# ---------------------------------------------------------------------------
# get_context_filter factory
# ---------------------------------------------------------------------------


class TestGetContextFilter:
    def test_full_string(self):
        f = get_context_filter("full")
        assert isinstance(f, FullContextFilter)

    def test_summary_string(self):
        f = get_context_filter("summary")
        assert isinstance(f, SummaryContextFilter)

    def test_isolated_string(self):
        f = get_context_filter("isolated")
        assert isinstance(f, IsolatedContextFilter)

    def test_case_insensitive(self):
        assert isinstance(get_context_filter("FULL"), FullContextFilter)
        assert isinstance(get_context_filter("Summary"), SummaryContextFilter)
        assert isinstance(get_context_filter("ISOLATED"), IsolatedContextFilter)

    def test_context_strategy_enum(self):
        f = get_context_filter(ContextStrategy.FULL)
        assert isinstance(f, FullContextFilter)

    def test_unknown_strategy_raises(self):
        with pytest.raises(ValueError, match="Unknown context strategy"):
            get_context_filter("nonexistent")


# ---------------------------------------------------------------------------
# compact_handoff_history
# ---------------------------------------------------------------------------


class TestCompactHandoffHistory:
    def test_short_history_unchanged(self):
        history = _make_history(5)
        result = compact_handoff_history(history, max_items=10)
        assert result == history

    def test_compresses_older_messages(self):
        history = _make_history(20)
        result = compact_handoff_history(history, max_items=6)
        # 1 summary + 6 recent = 7
        assert len(result) == 7

    def test_summary_counts_by_role(self):
        history = [
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "u2"},
            {"role": "assistant", "content": "a2"},
            {"role": "user", "content": "u3"},
            {"role": "assistant", "content": "a3"},
        ]
        result = compact_handoff_history(history, max_items=2)
        summary = result[0]
        assert "2 user" in summary["content"]
        assert "2 assistant" in summary["content"]

    def test_empty_older_messages(self):
        # max_items >= len(history) → no compression
        history = _make_history(3)
        result = compact_handoff_history(history, max_items=5)
        assert result == history

    def test_preserves_recent_order(self):
        history = _make_history(10)
        result = compact_handoff_history(history, max_items=4)
        assert result[-4:] == history[-4:]


# ---------------------------------------------------------------------------
# HandoffResult
# ---------------------------------------------------------------------------


class TestHandoffResult:
    def test_basic_creation(self):
        r = HandoffResult(from_agent="a1", to_agent="a2")
        assert r.from_agent == "a1"
        assert r.to_agent == "a2"
        assert r.context_strategy == ""
        assert r.messages_passed == 0

    def test_with_strategy_and_count(self):
        r = HandoffResult(
            from_agent="a1",
            to_agent="a2",
            context_strategy="summary",
            messages_passed=5,
        )
        assert r.context_strategy == "summary"
        assert r.messages_passed == 5
