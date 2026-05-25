"""E2E framework validation — verify test infrastructure works."""
from __future__ import annotations

import pytest

from .conftest import e2e_skip, create_e2e_llm, create_e2e_engine, get_e2e_model


@e2e_skip
@pytest.mark.e2e
def test_e2e_endpoint_connectivity():
    """E2E endpoint is reachable and returns responses."""
    llm = create_e2e_llm()
    # Simple call to verify connectivity
    result = llm([{"role": "user", "content": "Say 'ok' and nothing else."}])
    assert result is not None
    assert len(str(result)) > 0


@e2e_skip
@pytest.mark.e2e
def test_e2e_llm_creates_successfully():
    """E2E LLM instance is created with correct config."""
    llm = create_e2e_llm()
    assert llm is not None
    model_name = getattr(llm, "model", "") or getattr(llm, "_model", "")
    assert model_name  # Should have a model name


@e2e_skip
@pytest.mark.e2e
def test_e2e_engine_creates_with_agent():
    """E2E Engine is created with a simple agent."""
    from ._agents import SimpleReActAgent
    llm = create_e2e_llm()
    agent = SimpleReActAgent(llm=llm)
    engine = create_e2e_engine(agent)
    assert engine is not None
    assert engine.agent is agent
