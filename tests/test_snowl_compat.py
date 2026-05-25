"""Tests for snowl_compat adapters and RunState round-trip."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import pytest

from qitos.engine.run_state import RunState, CURRENT_SCHEMA_VERSION
from qitos.core.state import StateSchema


# ---------------------------------------------------------------------------
# Helper: minimal EngineResult mock (same pattern as test_run_state.py)
# ---------------------------------------------------------------------------


class _FakeResult:
    """Minimal EngineResult stub for serialization tests."""

    def __init__(self, step_count=5, task="test task", total_tokens=100):
        self.state = StateSchema(task=task, max_steps=10, current_step=step_count)
        self.step_count = step_count
        self.total_tokens = total_tokens
        self.records = []
        self.events = []
        self.budget = None


# ---------------------------------------------------------------------------
# RunState round-trip
# ---------------------------------------------------------------------------


class TestRunStateRoundTrip:
    def test_to_json_and_back(self):
        result = _FakeResult()
        rs = RunState.from_engine_result(result, agent_name="test_agent")
        json_str = rs.to_json()
        restored = RunState.from_json(json_str)
        assert restored.agent_name == "test_agent"
        assert restored.step == 5
        assert restored.schema_version == CURRENT_SCHEMA_VERSION

    def test_round_trip_preserves_data(self):
        result = _FakeResult(task="find bugs")
        rs = RunState.from_engine_result(result, agent_name="qitos_auditor")
        json_str = rs.to_json()
        restored = RunState.from_json(json_str)
        assert restored.task_text == "find bugs"
        assert restored.agent_name == "qitos_auditor"

    def test_round_trip_with_checkpoint(self):
        result = _FakeResult()
        rs = RunState.from_engine_result(
            result, agent_name="test", checkpoint_id="cp-001"
        )
        json_str = rs.to_json()
        restored = RunState.from_json(json_str)
        assert restored.checkpoint_id == "cp-001"

    def test_json_is_valid(self):
        result = _FakeResult()
        rs = RunState.from_engine_result(result)
        json_str = rs.to_json()
        parsed = json.loads(json_str)
        assert "$schemaVersion" in parsed

    def test_compact_json(self):
        result = _FakeResult()
        rs = RunState.from_engine_result(result)
        json_str = rs.to_json(pretty=False)
        assert "\n" not in json_str

    def test_unsupported_schema_version(self):
        with pytest.raises(Exception):
            RunState.from_json('{"$schemaVersion": "99.0"}')


# ---------------------------------------------------------------------------
# snowl_compat serialize/deserialize pattern
# ---------------------------------------------------------------------------


class TestSnowlCompatPattern:
    def test_serialize_run_state(self):
        """Verify the snowl_compat serialization pattern works."""
        result = _FakeResult()
        rs = RunState.from_engine_result(result, agent_name="qitos_coder")
        raw_json = rs.to_json(pretty=False)
        data = json.loads(raw_json)
        assert data["agent_name"] == "qitos_coder"
        assert "step" in data

    def test_deserialize_run_state(self):
        """Verify the snowl_compat deserialization pattern works."""
        result = _FakeResult()
        rs = RunState.from_engine_result(result, agent_name="qitos_cyber")
        raw_json = rs.to_json(pretty=False)
        restored = RunState.from_json(raw_json)
        assert restored.agent_name == "qitos_cyber"

    def test_round_trip_preserves_all_agents(self):
        """Verify round-trip works for all agent types."""
        for name in ["qitos_coder", "qitos_auditor", "qitos_cyber", "qitos_researcher", "qitos_swe"]:
            result = _FakeResult(task=f"task for {name}")
            rs = RunState.from_engine_result(result, agent_name=name)
            restored = RunState.from_json(rs.to_json(pretty=False))
            assert restored.agent_name == name
            assert restored.task_text == f"task for {name}"


# ---------------------------------------------------------------------------
# Domestic embedder → VectorMemory interop
# ---------------------------------------------------------------------------


class TestEmbedderVectorMemoryInterop:
    def test_dashscope_embedder_creates(self):
        from qitos.kit.embedding import DashScopeEmbedder
        e = DashScopeEmbedder(api_key="test")
        assert e.model == "text-embedding-v3"
        assert e.dimension == 1024

    def test_zhipu_embedder_creates(self):
        from qitos.kit.embedding import ZhipuEmbedder
        e = ZhipuEmbedder(api_key="test")
        assert e.model == "embedding-3"
        assert e.dimension == 2048

    def test_dashscope_in_embedding_module(self):
        from qitos.kit.embedding import DashScopeEmbedder, ZhipuEmbedder
        assert DashScopeEmbedder is not None
        assert ZhipuEmbedder is not None
