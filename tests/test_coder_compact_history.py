"""Tests for CompactHistory integration in the ClaudeCodeAgent."""

from __future__ import annotations

import os
from typing import Any

import pytest

from qitos.core.history import HistoryMessage
from qitos.kit.history.compact_history import (
    CompactConfig,
    CompactHistory,
    compact_history,
)


# ---------------------------------------------------------------------------
# Helper: lazy import of ClaudeCodeAgent
# ---------------------------------------------------------------------------

_AGENT_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "plans",
    "qitos_zoo_migration",
    "apps",
    "qitos-coder",
)


def _import_agent():
    """Import ClaudeCodeAgent lazily, adding its package root to sys.path."""
    import sys

    agent_dir = os.path.abspath(_AGENT_DIR)
    if agent_dir not in sys.path:
        sys.path.insert(0, agent_dir)
    from claude_code.agent import ClaudeCodeAgent, ClaudeCodeState

    return ClaudeCodeAgent, ClaudeCodeState


# ---------------------------------------------------------------------------
# 1. CompactHistory can be created with coding-specific config
# ---------------------------------------------------------------------------

class TestCodingCompactConfig:
    """Verify coding-specific CompactConfig behaves as expected."""

    def test_coding_config_has_larger_token_budget(self) -> None:
        cfg = CompactConfig(
            max_tokens=32000,
            keep_last_rounds=2,
            keep_last_messages=10,
            hard_window=128,
        )
        assert cfg.max_tokens == 32000
        assert cfg.max_tokens > CompactConfig().max_tokens  # 16k default

    def test_coding_config_preserves_fewer_rounds(self) -> None:
        cfg = CompactConfig(
            max_tokens=32000,
            keep_last_rounds=2,
            keep_last_messages=10,
            hard_window=128,
        )
        assert cfg.keep_last_rounds == 2
        # Default is also 2, but coding config is explicit about it

    def test_coding_config_larger_hard_window(self) -> None:
        cfg = CompactConfig(
            max_tokens=32000,
            keep_last_rounds=2,
            keep_last_messages=10,
            hard_window=128,
        )
        assert cfg.hard_window == 128
        assert cfg.hard_window > CompactConfig().hard_window  # 96 default

    def test_compact_history_builder_with_coding_config(self) -> None:
        cfg = CompactConfig(
            max_tokens=32000,
            keep_last_rounds=2,
            keep_last_messages=10,
            hard_window=128,
            auto_compact=True,
        )
        ch = compact_history(config=cfg)
        assert isinstance(ch, CompactHistory)
        assert ch.config.max_tokens == 32000
        assert ch.config.hard_window == 128
        assert ch.config.auto_compact is True

    def test_compact_history_builder_with_kwargs(self) -> None:
        ch = compact_history(
            max_tokens=32000,
            keep_last_rounds=2,
            keep_last_messages=10,
            hard_window=128,
        )
        assert isinstance(ch, CompactHistory)
        assert ch.config.max_tokens == 32000


# ---------------------------------------------------------------------------
# 2. The agent's engine creation accepts CompactHistory
# ---------------------------------------------------------------------------

class TestAgentCompactHistoryIntegration:
    """Verify ClaudeCodeAgent creates and accepts CompactHistory."""

    def test_agent_creates_default_compact_history(self) -> None:
        ClaudeCodeAgent, _ = _import_agent()
        agent = ClaudeCodeAgent(workspace_root=".")
        assert isinstance(agent.history, CompactHistory)
        assert agent.history.config.max_tokens == 32000
        assert agent.history.config.keep_last_rounds == 2
        assert agent.history.config.keep_last_messages == 10
        assert agent.history.config.hard_window == 128

    def test_agent_accepts_custom_compact_history(self) -> None:
        ClaudeCodeAgent, _ = _import_agent()
        custom = compact_history(
            max_tokens=64000,
            keep_last_rounds=5,
            keep_last_messages=20,
            hard_window=200,
        )
        agent = ClaudeCodeAgent(workspace_root=".", history=custom)
        assert agent.history is custom
        assert agent.history.config.max_tokens == 64000
        assert agent.history.config.keep_last_rounds == 5

    def test_agent_history_is_passed_to_super(self) -> None:
        """Verify the history lands on AgentModule.history via super().__init__."""
        ClaudeCodeAgent, _ = _import_agent()
        custom = compact_history(max_tokens=50000)
        agent = ClaudeCodeAgent(workspace_root=".", history=custom)
        # AgentModule stores it as self.history
        assert hasattr(agent, "history")
        assert agent.history is custom


# ---------------------------------------------------------------------------
# 3. Long message history triggers compaction events
# ---------------------------------------------------------------------------

class TestCompactionEventsOnLongHistory:
    """Verify that a long conversation triggers compaction in the agent's history."""

    def _build_verbose_history(self) -> CompactHistory:
        """Create a CompactHistory with a tight budget to force compaction."""
        return CompactHistory(
            max_tokens=120,
            keep_last_rounds=1,
            keep_last_messages=4,
            hard_window=24,
            auto_compact=True,
        )

    def _populate_history(self, history: CompactHistory, n_steps: int = 8) -> None:
        """Add many long messages to push past the budget."""
        for idx in range(n_steps):
            role = "user" if idx % 2 == 0 else "assistant"
            history.append(
                HistoryMessage(
                    role=role,
                    content=(
                        f"Step {idx}: "
                        + "This is a verbose message with lots of code context. " * 60
                    ).strip(),
                    step_id=idx,
                    metadata={"source": "engine"},
                )
            )

    def test_retrieve_returns_compacted_messages(self) -> None:
        history = self._build_verbose_history()
        self._populate_history(history)
        retrieved = history.retrieve(
            query={
                "roles": ["user", "assistant"],
                "max_items": 24,
                "max_tokens": 120,
                "pending_content": "next turn",
            }
        )
        # Should have fewer messages than were appended
        assert len(retrieved) < 8
        # First message should be a summary
        assert retrieved[0].metadata.get("summary") is True

    def test_warning_event_emitted(self) -> None:
        history = self._build_verbose_history()
        self._populate_history(history)
        history.retrieve(
            query={
                "roles": ["user", "assistant"],
                "max_tokens": 120,
                "pending_content": "next turn",
            }
        )
        events = history.consume_runtime_events()
        stages = [
            (e.get("context") or {}).get("stage")
            for e in events
            if e.get("stage") == "context_history"
        ]
        assert "warning" in stages

    def test_microcompact_or_summary_event_emitted(self) -> None:
        history = self._build_verbose_history()
        self._populate_history(history)
        history.retrieve(
            query={
                "roles": ["user", "assistant"],
                "max_tokens": 120,
                "pending_content": "next turn",
            }
        )
        events = history.consume_runtime_events()
        stages = [
            (e.get("context") or {}).get("stage")
            for e in events
            if e.get("stage") == "context_history"
        ]
        assert any(
            s in {"microcompact_applied", "summary_compact_applied"}
            for s in stages
        )

    def test_agent_history_compaction_on_long_session(self) -> None:
        """End-to-end: agent's built-in CompactHistory compacts long sessions."""
        ClaudeCodeAgent, _ = _import_agent()
        # Use a very tight budget to force compaction in the test
        agent = ClaudeCodeAgent(
            workspace_root=".",
            history=CompactHistory(
                max_tokens=100,
                keep_last_rounds=1,
                keep_last_messages=4,
                hard_window=20,
                auto_compact=True,
            ),
        )
        history = agent.history
        assert isinstance(history, CompactHistory)

        # Simulate a long coding session
        for idx in range(10):
            role = "user" if idx % 2 == 0 else "assistant"
            history.append(
                HistoryMessage(
                    role=role,
                    content=(
                        f"Step {idx}: "
                        + "Reading and editing files with detailed output. " * 50
                    ).strip(),
                    step_id=idx,
                    metadata={"source": "engine"},
                )
            )

        retrieved = history.retrieve(
            query={
                "roles": ["user", "assistant"],
                "max_tokens": 100,
                "pending_content": "next prompt",
            }
        )
        events = history.consume_runtime_events()

        # Compaction happened
        assert len(retrieved) < 10
        # Events were emitted
        context_stages = [
            (e.get("context") or {}).get("stage")
            for e in events
            if e.get("stage") == "context_history"
        ]
        assert "warning" in context_stages
        assert any(
            s in {"microcompact_applied", "summary_compact_applied"}
            for s in context_stages
        )

    def test_metadata_tracks_compacted_messages(self) -> None:
        history = self._build_verbose_history()
        self._populate_history(history)
        history.retrieve(
            query={
                "roles": ["user", "assistant"],
                "max_tokens": 120,
                "pending_content": "next turn",
            }
        )
        metadata = history.get_last_message_metadata()
        assert isinstance(metadata, list)
        # At least one message should be a summary
        assert any(m.get("summary") for m in metadata)
