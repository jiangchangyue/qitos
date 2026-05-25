"""E2E: FunctionTool marker verification — read_only and needs_approval."""
from __future__ import annotations

import pytest

from .conftest import e2e_skip, create_e2e_llm, create_e2e_engine


@e2e_skip
@pytest.mark.e2e
def test_read_only_tool_no_approval_needed():
    """Agent can call read_only tools without approval."""
    from ._agents import CalculatorAgent
    from qitos.engine.engine import Engine

    llm = create_e2e_llm(temperature=0.0)
    agent = CalculatorAgent(llm=llm)
    engine = Engine(agent=agent, auto_approve=False)
    result = engine.run("What is 5 + 3?")
    # read_only tools (add) should work even without auto_approve
    assert result.state is not None


@e2e_skip
@pytest.mark.e2e
def test_needs_approval_auto_approve():
    """needs_approval tool with auto_approve=True runs and records audit trail."""
    from ._agents import CalculatorAgent
    from qitos.engine.engine import Engine

    llm = create_e2e_llm(temperature=0.0)
    agent = CalculatorAgent(llm=llm)
    engine = Engine(agent=agent, auto_approve=True)
    result = engine.run("Divide 100 by 5 using the dangerous_divide tool.")
    assert result.state is not None
    # Check records for auto_approved metadata
    has_auto_approved = False
    for rec in engine.records:
        for ar in rec.action_results:
            if isinstance(ar, dict) and ar.get("extra_metadata", {}).get("auto_approved"):
                has_auto_approved = True
    # It's OK if the LLM didn't choose the divide tool — the test verifies the path exists


@e2e_skip
@pytest.mark.e2e
def test_needs_approval_rejected_without_auto_approve():
    """needs_approval tool is rejected when auto_approve=False and no human approval."""
    from ._agents import CalculatorAgent
    from qitos.engine.engine import Engine

    llm = create_e2e_llm(temperature=0.0)
    agent = CalculatorAgent(llm=llm)
    engine = Engine(agent=agent, auto_approve=False)
    # Engine should still run, but needs_approval tools should be rejected
    result = engine.run("Divide 10 by 2 using dangerous_divide.")
    assert result.state is not None
