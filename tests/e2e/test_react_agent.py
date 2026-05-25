"""E2E: ReAct agent basic loop — tool calling + reasoning."""
from __future__ import annotations

import pytest

from .conftest import e2e_skip, create_e2e_llm, create_e2e_engine


@e2e_skip
@pytest.mark.e2e
def test_react_simple_tool_call():
    """ReAct agent calls calculator tools and combines results."""
    from ._agents import CalculatorAgent
    llm = create_e2e_llm(temperature=0.0)
    agent = CalculatorAgent(llm=llm)
    engine = create_e2e_engine(agent, auto_approve=True)
    result = engine.run("What is 15 + 27?")
    assert result.state is not None
    assert result.state.final_result is not None
    # The answer should contain 42
    assert "42" in str(result.state.final_result)


@e2e_skip
@pytest.mark.e2e
def test_react_multi_step_reasoning():
    """ReAct agent performs multi-step tool calling."""
    from ._agents import CalculatorAgent
    llm = create_e2e_llm(temperature=0.0)
    agent = CalculatorAgent(llm=llm)
    engine = create_e2e_engine(agent, auto_approve=True)
    result = engine.run("First add 10 and 20, then multiply the result by 3.")
    assert result.state is not None
    assert result.state.final_result is not None
    # 10+20=30, 30*3=90
    assert "90" in str(result.state.final_result)


@e2e_skip
@pytest.mark.e2e
def test_react_direct_answer():
    """ReAct agent provides final answer without tool calls."""
    from ._agents import SimpleReActAgent
    llm = create_e2e_llm(temperature=0.0)
    agent = SimpleReActAgent(llm=llm)
    engine = create_e2e_engine(agent)
    result = engine.run("What is the capital of France? Answer in one word.")
    assert result.state is not None
    assert result.state.final_result is not None
    assert "Paris" in str(result.state.final_result) or "paris" in str(result.state.final_result).lower()


@e2e_skip
@pytest.mark.e2e
def test_react_max_steps_limit():
    """Engine stops at max_steps even if agent wants to continue."""
    from ._agents import SimpleReActAgent
    llm = create_e2e_llm(temperature=0.0)
    agent = SimpleReActAgent(llm=llm)
    from qitos.engine.states import RuntimeBudget
    engine = create_e2e_engine(agent, budget=RuntimeBudget(max_steps=2))
    result = engine.run("Keep thinking about numbers. Never stop.")
    assert result.state is not None
    # Should have stopped due to max_steps
    assert result.state.current_step <= 3  # max_steps=2 means at most 2 full steps
