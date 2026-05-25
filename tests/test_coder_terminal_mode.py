"""Tests for ClaudeCodeAgent handoff_targets and TerminalModeAgent."""
from __future__ import annotations

from unittest.mock import MagicMock


def test_claude_code_agent_has_handoff_targets():
    """ClaudeCodeAgent declares handoff_targets."""
    from qitos_zoo.qitos_coder import ClaudeCodeAgent
    assert hasattr(ClaudeCodeAgent, "handoff_targets")
    assert "terminal_agent" in ClaudeCodeAgent.handoff_targets


def test_terminal_mode_agent_instantiable():
    """TerminalModeAgent can be instantiated."""
    from qitos_zoo.qitos_coder import TerminalModeAgent
    agent = TerminalModeAgent(llm=MagicMock())
    assert agent.name == "terminal_agent"


def test_terminal_mode_agent_init_state():
    """TerminalModeAgent creates TerminalState."""
    from qitos_zoo.qitos_coder import TerminalModeAgent
    agent = TerminalModeAgent(llm=MagicMock())
    state = agent.init_state("test task")
    assert state.task == "test task"
    assert state.max_steps == 20


def test_coder_handoff_tools_registered():
    """Engine registers transfer_to_terminal_agent when ClaudeCodeAgent has handoff_targets."""
    from qitos_zoo.qitos_coder import ClaudeCodeAgent, TerminalModeAgent
    from qitos.core.agent_spec import AgentRegistry, AgentSpec
    from qitos.engine.engine import Engine

    agent = ClaudeCodeAgent(llm=MagicMock(), workspace_root=".")
    terminal = TerminalModeAgent(llm=MagicMock())

    registry = AgentRegistry()
    registry.register(AgentSpec(name="terminal_agent", description="Terminal interaction agent", agent=terminal))

    engine = Engine(agent=agent, agent_registry=registry, auto_approve=True)
    tool_names = engine.tool_registry.list_tools()
    # list_tools returns tool names (strings) or tool objects
    if tool_names and hasattr(tool_names[0], 'spec'):
        tool_names = [t.spec.name for t in tool_names]
    assert "transfer_to_terminal_agent" in tool_names
