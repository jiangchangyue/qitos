"""Tests for PrimaryPentestAgent handoff_targets wiring."""
from __future__ import annotations

from unittest.mock import MagicMock


def test_primary_agent_has_handoff_targets():
    """PrimaryPentestAgent declares handoff_targets."""
    from qitos_zoo.qitos_cyber.pentagi.agents.primary import PrimaryPentestAgent
    assert hasattr(PrimaryPentestAgent, "handoff_targets")
    targets = PrimaryPentestAgent.handoff_targets
    assert isinstance(targets, list)
    assert len(targets) >= 5


def test_handoff_targets_include_specialists():
    """handoff_targets include all specialist agent names."""
    from qitos_zoo.qitos_cyber.pentagi.agents.primary import PrimaryPentestAgent
    targets = PrimaryPentestAgent.handoff_targets
    expected = {"pentester", "coder", "maintenance", "search", "memorist"}
    assert expected.issubset(set(targets)), f"Missing targets: {expected - set(targets)}"


def test_handoff_targets_excludes_adviser():
    """Primary agent excludes adviser from handoff_targets (adviser is invoked separately)."""
    from qitos_zoo.qitos_cyber.pentagi.agents.primary import PrimaryPentestAgent
    targets = PrimaryPentestAgent.handoff_targets
    assert "adviser" not in targets


def test_primary_agent_instance_inherits_handoff_targets():
    """PrimaryPentestAgent instance has handoff_targets from class."""
    from qitos_zoo.qitos_cyber.pentagi.agents.primary import PrimaryPentestAgent
    agent = PrimaryPentestAgent(llm=MagicMock())
    assert agent.handoff_targets == PrimaryPentestAgent.handoff_targets


def test_handoff_targets_match_delegate_permissions():
    """handoff_targets match AGENT_DELEGATION_PERMISSIONS for primary."""
    from qitos_zoo.qitos_cyber.pentagi.agents.primary import PrimaryPentestAgent
    from qitos_zoo.qitos_cyber.pentagi.tools.pentest_delegate import AGENT_DELEGATION_PERMISSIONS
    targets = set(PrimaryPentestAgent.handoff_targets)
    # Map handoff target names to delegate names
    delegate_map = {
        "pentester": "pentester",
        "coder": "coder",
        "maintenance": "installer",
        "search": "searcher",
        "memorist": "memorist",
    }
    delegate_targets = {delegate_map[t] for t in targets if t in delegate_map}
    primary_perms = AGENT_DELEGATION_PERMISSIONS.get("primary", set())
    # Exclude adviser from comparison (handoff_targets excludes it by design)
    primary_perms_no_adviser = primary_perms - {"adviser"}
    assert delegate_targets == primary_perms_no_adviser
