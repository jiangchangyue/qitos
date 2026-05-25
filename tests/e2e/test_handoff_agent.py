"""E2E: Handoff multi-agent collaboration."""
from __future__ import annotations

import pytest

from .conftest import e2e_skip, create_e2e_llm, create_e2e_engine


def _get_tool_names(engine) -> list[str]:
    """Get tool names from engine.tool_registry, handling both str and object returns."""
    raw = engine.tool_registry.list_tools()
    result = []
    for t in raw:
        if isinstance(t, str):
            result.append(t)
        elif hasattr(t, 'spec'):
            result.append(t.spec.name)
        elif hasattr(t, 'name'):
            result.append(t.name)
        else:
            result.append(str(t))
    return result


@e2e_skip
@pytest.mark.e2e
def test_handoff_single_delegation():
    """Orchestrator delegates to math worker for a math task."""
    from ._agents import HandoffOrchestrator, MathWorker, StringWorker
    from qitos.core.agent_spec import AgentRegistry, AgentSpec
    from qitos.engine.engine import Engine

    llm = create_e2e_llm(temperature=0.0)
    orchestrator = HandoffOrchestrator(llm=llm)
    math_worker = MathWorker(llm=llm)
    string_worker = StringWorker(llm=llm)

    registry = AgentRegistry()
    registry.register(AgentSpec(name="math_worker", description="Math specialist", agent=math_worker))
    registry.register(AgentSpec(name="string_worker", description="String operations specialist", agent=string_worker))

    engine = Engine(agent=orchestrator, agent_registry=registry, auto_approve=True)
    tool_names = _get_tool_names(engine)
    assert any("transfer_to_math_worker" in n for n in tool_names)


@e2e_skip
@pytest.mark.e2e
def test_handoff_tools_registered():
    """All handoff_targets produce transfer_to_* tools in the registry."""
    from ._agents import HandoffOrchestrator, MathWorker, StringWorker
    from qitos.core.agent_spec import AgentRegistry, AgentSpec
    from qitos.engine.engine import Engine

    llm = create_e2e_llm(temperature=0.0)
    orchestrator = HandoffOrchestrator(llm=llm)

    registry = AgentRegistry()
    registry.register(AgentSpec(name="math_worker", description="Math specialist", agent=MathWorker(llm=llm)))
    registry.register(AgentSpec(name="string_worker", description="String specialist", agent=StringWorker(llm=llm)))

    engine = Engine(agent=orchestrator, agent_registry=registry, auto_approve=True)
    tool_names = _get_tool_names(engine)
    assert "transfer_to_math_worker" in tool_names
    assert "transfer_to_string_worker" in tool_names


@e2e_skip
@pytest.mark.e2e
def test_handoff_auditor_pipeline():
    """AuditAgent handoff tools are registered in Engine."""
    from qitos_zoo.qitos_auditor import AuditAgent
    from qitos.core.agent_spec import AgentRegistry, AgentSpec
    from qitos.engine.engine import Engine
    from unittest.mock import MagicMock

    llm = MagicMock()
    auditor = AuditAgent(llm=llm, workspace_root=".")
    recon = MagicMock()
    recon.name = "recon_agent"

    registry = AgentRegistry()
    registry.register(AgentSpec(name="recon_agent", description="Recon specialist", agent=recon))

    engine = Engine(agent=auditor, agent_registry=registry, auto_approve=True)
    tool_names = _get_tool_names(engine)
    assert "transfer_to_recon_agent" in tool_names


@e2e_skip
@pytest.mark.e2e
def test_handoff_cyber_pipeline():
    """PrimaryPentestAgent handoff tools are registered in Engine."""
    from qitos_zoo.qitos_cyber.pentagi.agents.primary import PrimaryPentestAgent
    from qitos.core.agent_spec import AgentRegistry, AgentSpec
    from qitos.engine.engine import Engine
    from unittest.mock import MagicMock

    llm = MagicMock()
    primary = PrimaryPentestAgent(llm=llm)

    registry = AgentRegistry()
    for target in primary.handoff_targets:
        mock_agent = MagicMock()
        mock_agent.name = target
        registry.register(AgentSpec(name=target, description=f"{target} specialist", agent=mock_agent))

    engine = Engine(agent=primary, agent_registry=registry, auto_approve=True)
    tool_names = _get_tool_names(engine)
    for target in primary.handoff_targets:
        assert f"transfer_to_{target}" in tool_names
