"""Tests for v0.7 AgentRegistry topology validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from qitos import AgentModule, AgentRegistry, AgentSpec, Decision, StateSchema


@dataclass
class TopoState(StateSchema):
    pass


class AgentA(AgentModule[TopoState, Any, Any]):
    name = "agent_a"
    handoff_targets = ["agent_b"]

    def init_state(self, task, **kwargs):
        return TopoState(task=task, max_steps=5)

    def reduce(self, state, observation, decision):
        return state


class AgentB(AgentModule[TopoState, Any, Any]):
    name = "agent_b"
    handoff_targets = ["agent_c"]

    def init_state(self, task, **kwargs):
        return TopoState(task=task, max_steps=5)

    def reduce(self, state, observation, decision):
        return state


class AgentC(AgentModule[TopoState, Any, Any]):
    name = "agent_c"
    handoff_targets = []

    def init_state(self, task, **kwargs):
        return TopoState(task=task, max_steps=5)

    def reduce(self, state, observation, decision):
        return state


class AgentCycle(AgentModule[TopoState, Any, Any]):
    name = "agent_cycle"
    handoff_targets = ["agent_cycle_back"]

    def init_state(self, task, **kwargs):
        return TopoState(task=task, max_steps=5)

    def reduce(self, state, observation, decision):
        return state


class AgentCycleBack(AgentModule[TopoState, Any, Any]):
    name = "agent_cycle_back"
    handoff_targets = ["agent_cycle"]

    def init_state(self, task, **kwargs):
        return TopoState(task=task, max_steps=5)

    def reduce(self, state, observation, decision):
        return state


class AgentUnknown(AgentModule[TopoState, Any, Any]):
    name = "agent_unknown"
    handoff_targets = ["nonexistent_agent"]

    def init_state(self, task, **kwargs):
        return TopoState(task=task, max_steps=5)

    def reduce(self, state, observation, decision):
        return state


class TestAgentRegistryTopology:
    def test_valid_chain_no_warnings(self):
        """A→B→C chain with all targets present has no cycle or unknown target warnings."""
        registry = AgentRegistry()
        registry.register(AgentSpec(name="agent_a", description="A", agent=AgentA()))
        registry.register(AgentSpec(name="agent_b", description="B", agent=AgentB()))
        registry.register(AgentSpec(name="agent_c", description="C", agent=AgentC()))

        warnings = registry.validate_topology()
        # Filter out "no inbound" warnings (informational only)
        serious = [w for w in warnings if "unknown" in w or "cycle" in w]
        assert len(serious) == 0

    def test_unknown_target_warning(self):
        """Agent referencing a non-existent handoff target produces a warning."""
        registry = AgentRegistry()
        registry.register(AgentSpec(name="agent_unknown", description="U", agent=AgentUnknown()))

        warnings = registry.validate_topology()
        unknown_warnings = [w for w in warnings if "unknown" in w.lower()]
        assert len(unknown_warnings) == 1
        assert "nonexistent_agent" in unknown_warnings[0]

    def test_cycle_detection(self):
        """A↔B cycle is detected."""
        registry = AgentRegistry()
        registry.register(AgentSpec(name="agent_cycle", description="C", agent=AgentCycle()))
        registry.register(AgentSpec(name="agent_cycle_back", description="CB", agent=AgentCycleBack()))

        warnings = registry.validate_topology()
        cycle_warnings = [w for w in warnings if "cycle" in w.lower()]
        assert len(cycle_warnings) >= 1

    def test_isolated_agent_warning(self):
        """Agent with no inbound handoff targets gets an informational warning."""
        registry = AgentRegistry()
        registry.register(AgentSpec(name="agent_a", description="A", agent=AgentA()))
        registry.register(AgentSpec(name="agent_c", description="C", agent=AgentC()))
        # agent_a hands off to agent_b (not registered), agent_c has no inbound

        warnings = registry.validate_topology()
        isolated_warnings = [w for w in warnings if "no inbound" in w.lower()]
        # At least agent_c should be flagged as isolated (no one hands off to it)
        assert len(isolated_warnings) >= 1

    def test_empty_registry_no_warnings(self):
        """Empty registry has no warnings."""
        registry = AgentRegistry()
        warnings = registry.validate_topology()
        assert warnings == []

    def test_single_agent_no_handoff_targets(self):
        """Single agent with no handoff targets: no warnings."""
        class Solo(AgentModule[TopoState, Any, Any]):
            name = "solo"
            handoff_targets = []

            def init_state(self, task, **kwargs):
                return TopoState(task=task, max_steps=5)

            def reduce(self, state, observation, decision):
                return state

        registry = AgentRegistry()
        registry.register(AgentSpec(name="solo", description="Solo", agent=Solo()))

        warnings = registry.validate_topology()
        # Single agent, no inbound is not a warning (len > 1 check)
        assert len(warnings) == 0

    def test_no_handoff_targets_attribute(self):
        """Agent without handoff_targets attribute: no crash, no unknown target warnings."""
        class NoTargets(AgentModule[TopoState, Any, Any]):
            name = "no_targets"

            def init_state(self, task, **kwargs):
                return TopoState(task=task, max_steps=5)

            def reduce(self, state, observation, decision):
                return state

        registry = AgentRegistry()
        registry.register(AgentSpec(name="no_targets", description="NT", agent=NoTargets()))

        warnings = registry.validate_topology()
        assert all("unknown" not in w for w in warnings)
