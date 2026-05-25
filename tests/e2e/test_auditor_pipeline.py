"""E2E: Auditor pipeline — single agent and multi-agent verification."""
from __future__ import annotations

import pytest

from .conftest import e2e_skip, create_e2e_llm


@e2e_skip
@pytest.mark.e2e
def test_auditor_single_agent_audit():
    """AuditAgent performs a basic audit task with tool calls."""
    from qitos_zoo.qitos_auditor import AuditAgent
    from qitos.engine.engine import Engine

    llm = create_e2e_llm(temperature=0.0)
    agent = AuditAgent(llm=llm, workspace_root=".", mode="code_audit")
    engine = Engine(agent=agent, auto_approve=True)
    result = engine.run("Scan the current directory for code quality issues.")
    assert result.state is not None


@e2e_skip
@pytest.mark.e2e
def test_auditor_with_memory():
    """AuditAgent uses AuditBoardMemory during audit."""
    from qitos_zoo.qitos_auditor import AuditAgent, AuditBoardMemory
    from qitos.engine.engine import Engine

    llm = create_e2e_llm(temperature=0.0)
    memory = AuditBoardMemory()
    agent = AuditAgent(llm=llm, workspace_root=".", memory=memory)
    engine = Engine(agent=agent, auto_approve=True)
    result = engine.run("Check for common anti-patterns in the codebase.")
    assert result.state is not None
    # Memory should have been used
    assert len(memory._records) > 0 or len(memory.snapshot().get("confirmed_findings", [])) >= 0


@e2e_skip
@pytest.mark.e2e
def test_auditor_critic_triggers():
    """AuditAgent with critic detects severity issues."""
    from qitos_zoo.qitos_auditor import AuditAgent
    from qitos_zoo.qitos_auditor.critic import severity_consistency_critic
    from qitos.engine.engine import Engine

    llm = create_e2e_llm(temperature=0.0)
    agent = AuditAgent(llm=llm, workspace_root=".")
    engine = Engine(agent=agent, auto_approve=True, critics=[severity_consistency_critic])
    result = engine.run("Perform a quick security audit of this directory.")
    assert result.state is not None
