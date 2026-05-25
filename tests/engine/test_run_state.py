"""Tests for RunState serialization."""

import json
import pytest
from qitos.engine.run_state import (
    RunState,
    CURRENT_SCHEMA_VERSION,
    SCHEMA_VERSION_SUMMARIES,
)
from qitos.core.state import StateSchema, StateMigrationError


class TestRunStateCreation:
    """Test RunState creation and field defaults."""

    def test_default_fields(self):
        rs = RunState()
        assert rs.schema_version == CURRENT_SCHEMA_VERSION
        assert rs.agent_name == ""
        assert rs.step == 0
        assert rs.state_data == {}
        assert rs.state_type == ""
        assert rs.records == []
        assert rs.events == []
        assert rs.checkpoint_id is None
        assert rs.trace_state is None
        assert rs.token_usage == 0

    def test_with_data(self):
        rs = RunState(
            agent_name="test_agent",
            step=5,
            task_text="do something",
            state_data={"task": "do something", "current_step": 5},
            state_type="qitos.core.state.StateSchema",
            token_usage=1000,
        )
        assert rs.agent_name == "test_agent"
        assert rs.step == 5
        assert rs.state_data["current_step"] == 5


class TestRunStateSerialization:
    """Test RunState JSON round-trip."""

    def test_round_trip(self):
        rs = RunState(
            agent_name="coder",
            step=3,
            task_text="fix bug",
            state_data={"task": "fix bug", "current_step": 3},
            state_type="qitos.core.state.StateSchema",
            records=[{"step_id": 1}],
            events=[{"phase": "DECIDE"}],
            checkpoint_id="cp_abc",
            token_usage=500,
        )
        json_str = rs.to_json()
        rs2 = RunState.from_json(json_str)
        assert rs2.agent_name == "coder"
        assert rs2.step == 3
        assert rs2.task_text == "fix bug"
        assert rs2.state_data == {"task": "fix bug", "current_step": 3}
        assert rs2.state_type == "qitos.core.state.StateSchema"
        assert rs2.records == [{"step_id": 1}]
        assert rs2.events == [{"phase": "DECIDE"}]
        assert rs2.checkpoint_id == "cp_abc"
        assert rs2.token_usage == 500

    def test_pretty_json(self):
        rs = RunState(agent_name="test")
        json_str = rs.to_json(pretty=True)
        assert "\n" in json_str
        parsed = json.loads(json_str)
        assert parsed["agent_name"] == "test"

    def test_compact_json(self):
        rs = RunState(agent_name="test")
        json_str = rs.to_json(pretty=False)
        assert "\n" not in json_str

    def test_schema_version_in_output(self):
        rs = RunState()
        json_str = rs.to_json()
        parsed = json.loads(json_str)
        assert "$schemaVersion" in parsed
        assert parsed["$schemaVersion"] == CURRENT_SCHEMA_VERSION

    def test_serialization_meta(self):
        rs = RunState()
        json_str = rs.to_json()
        parsed = json.loads(json_str)
        assert "_serialization_meta" in parsed
        assert "original_type" in parsed["_serialization_meta"]


class TestRunStateSchemaVersioning:
    """Test schema versioning behavior."""

    def test_current_version_has_summary(self):
        assert CURRENT_SCHEMA_VERSION in SCHEMA_VERSION_SUMMARIES
        assert SCHEMA_VERSION_SUMMARIES[CURRENT_SCHEMA_VERSION] != ""

    def test_fail_fast_on_newer_version(self):
        json_str = json.dumps({
            "$schemaVersion": "99.0",
            "agent_name": "test",
            "step": 0,
            "state_data": {},
        })
        with pytest.raises(StateMigrationError, match="Unsupported"):
            RunState.from_json(json_str)

    def test_accepts_current_version(self):
        json_str = json.dumps({
            "$schemaVersion": CURRENT_SCHEMA_VERSION,
            "agent_name": "test",
            "step": 0,
            "state_data": {},
        })
        rs = RunState.from_json(json_str)
        assert rs.agent_name == "test"


class TestRunStateFromEngineResult:
    """Test RunState.from_engine_result()."""

    def test_from_simple_state(self):
        schema = StateSchema(task="hello", current_step=3)

        class FakeResult:
            step_count = 3
            total_tokens = 100
            records = []
            events = []
            budget = None
            state = schema

        rs = RunState.from_engine_result(FakeResult(), agent_name="test_agent")
        assert rs.agent_name == "test_agent"
        assert rs.step == 3
        assert rs.state_data["task"] == "hello"
        assert rs.token_usage == 100
        assert "StateSchema" in rs.state_type


class TestRunStateContextSerializer:
    """Test context serializer/deserializer hooks."""

    def test_custom_serializer(self):
        rs = RunState(state_data={"custom": True})

        def my_serializer(data):
            return {"__custom": data}

        json_str = rs.to_json(context_serializer=my_serializer)
        parsed = json.loads(json_str)
        assert "__custom" in parsed["state_data"]
        assert parsed["_serialization_meta"]["serialized_via"] == "context_serializer"
        assert parsed["_serialization_meta"]["requires_deserializer"] is True

    def test_custom_deserializer(self):
        json_str = json.dumps({
            "$schemaVersion": CURRENT_SCHEMA_VERSION,
            "state_data": {"__custom": {"x": 1}},
            "_serialization_meta": {
                "requires_deserializer": True,
            },
        })

        def my_deserializer(data):
            return data["__custom"]

        rs = RunState.from_json(json_str, context_deserializer=my_deserializer)
        assert rs.state_data == {"x": 1}
