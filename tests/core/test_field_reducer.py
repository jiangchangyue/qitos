"""Tests for field-level reducer (channel) semantics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Dict, List, Optional

import pytest

from qitos.core.channel import Append, Replace, Ephemeral, last_value, append_list, dict_merge, add_messages
from qitos.core.field_reducers import FieldReducerRegistry
from qitos.core.state import StateSchema


# --- Channel built-in reducer tests ---


class TestAppend:
    def test_append_lists(self):
        r = Append()
        assert r([1, 2], [3, 4]) == [1, 2, 3, 4]

    def test_append_dicts(self):
        r = Append()
        assert r({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}

    def test_append_dict_overwrite(self):
        r = Append()
        assert r({"a": 1}, {"a": 2}) == {"a": 2}

    def test_append_mismatched_types_fallback(self):
        r = Append()
        assert r("old", "new") == "new"

    def test_append_empty_current(self):
        r = Append()
        assert r([], [1, 2]) == [1, 2]


class TestReplace:
    def test_replace(self):
        r = Replace()
        assert r("old", "new") == "new"

    def test_replace_none(self):
        r = Replace()
        assert r(None, 42) == 42


class TestEphemeral:
    def test_ephemeral_replaces(self):
        r = Ephemeral()
        assert r("old", "new") == "new"

    def test_ephemeral_reset_value_default(self):
        r = Ephemeral()
        assert r.reset_value is None

    def test_ephemeral_custom_reset(self):
        r = Ephemeral(reset_value="")
        assert r.reset_value == ""


class TestBuiltinReducers:
    def test_last_value(self):
        assert last_value("a", "b") == "b"

    def test_append_list(self):
        assert append_list([1], [2, 3]) == [1, 2, 3]

    def test_append_list_none_current(self):
        assert append_list(None, [1]) == [1]

    def test_dict_merge(self):
        assert dict_merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}

    def test_dict_merge_overwrite(self):
        assert dict_merge({"a": 1}, {"a": 2}) == {"a": 2}

    def test_add_messages_append(self):
        current = [{"id": "1", "text": "hi"}]
        update = [{"id": "2", "text": "bye"}]
        result = add_messages(current, update)
        assert len(result) == 2

    def test_add_messages_replace_by_id(self):
        current = [{"id": "1", "text": "hi"}, {"id": "2", "text": "bye"}]
        update = [{"id": "1", "text": "hello"}]
        result = add_messages(current, update)
        assert len(result) == 2
        assert result[0]["text"] == "hello"
        assert result[1]["text"] == "bye"

    def test_add_messages_none(self):
        result = add_messages(None, [{"id": "1", "text": "hi"}])
        assert len(result) == 1


# --- FieldReducerRegistry tests ---


@dataclass
class SampleState(StateSchema):
    findings: Annotated[list, Append] = field(default_factory=list)
    current_phase: str = ""  # Default: Replace
    route_signal: Annotated[str, Ephemeral] = ""
    notes: Annotated[dict, Append] = field(default_factory=dict)


class TestFieldReducerRegistry:
    def test_from_schema_detects_annotated_fields(self):
        registry = FieldReducerRegistry.from_schema(SampleState)
        assert registry.has_reducer("findings")
        assert registry.has_reducer("route_signal")
        assert registry.has_reducer("notes")
        assert not registry.has_reducer("current_phase")

    def test_ephemeral_detection(self):
        registry = FieldReducerRegistry.from_schema(SampleState)
        assert registry.is_ephemeral("route_signal")
        assert not registry.is_ephemeral("findings")

    def test_apply_append(self):
        registry = FieldReducerRegistry.from_schema(SampleState)
        state = SampleState(findings=[1, 2])
        result = registry.apply("findings", state.findings, [3, 4])
        assert result == [1, 2, 3, 4]

    def test_apply_replace_default(self):
        registry = FieldReducerRegistry.from_schema(SampleState)
        result = registry.apply("current_phase", "old", "new")
        assert result == "new"

    def test_apply_all(self):
        registry = FieldReducerRegistry.from_schema(SampleState)
        state = SampleState(findings=[1], current_phase="init", route_signal="go", notes={"a": 1})
        result = registry.apply_all(state, {
            "findings": [2, 3],
            "current_phase": "analysis",
            "route_signal": "stop",
            "notes": {"b": 2},
        })
        assert result["findings"] == [1, 2, 3]
        assert result["current_phase"] == "analysis"
        assert result["route_signal"] == "stop"
        assert result["notes"] == {"a": 1, "b": 2}

    def test_reset_ephemeral(self):
        registry = FieldReducerRegistry.from_schema(SampleState)
        state = SampleState(route_signal="go")
        registry.reset_ephemeral(state)
        assert state.route_signal is None

    def test_plain_state_no_reducers(self):
        """StateSchema with no Annotated fields has no reducers."""
        registry = FieldReducerRegistry.from_schema(StateSchema)
        assert not registry.has_reducer("task")
        assert not registry.has_reducer("current_step")


# --- StateSchema.reduce_update() tests ---


class TestStateReduceUpdate:
    def test_reduce_update_append(self):
        state = SampleState(findings=[1, 2])
        state.reduce_update({"findings": [3, 4]})
        assert state.findings == [1, 2, 3, 4]

    def test_reduce_update_replace(self):
        state = SampleState(current_phase="init")
        state.reduce_update({"current_phase": "analysis"})
        assert state.current_phase == "analysis"

    def test_reduce_update_ephemeral(self):
        state = SampleState(route_signal="")
        state.reduce_update({"route_signal": "go"})
        assert state.route_signal == "go"

    def test_reduce_update_mixed(self):
        state = SampleState(findings=[1], current_phase="init", route_signal="", notes={"a": 1})
        state.reduce_update({
            "findings": [2],
            "current_phase": "running",
            "route_signal": "go",
            "notes": {"b": 2},
        })
        assert state.findings == [1, 2]
        assert state.current_phase == "running"
        assert state.route_signal == "go"
        assert state.notes == {"a": 1, "b": 2}

    def test_backward_compatible_no_reducers(self):
        """StateSchema without Annotated fields behaves identically to __dict__.update()."""
        state = StateSchema(task="hello", current_step=1)
        state.reduce_update({"task": "world", "current_step": 2})
        assert state.task == "world"
        assert state.current_step == 2


# --- Function-based reducer test ---


def my_reducer(current: int, update: int) -> int:
    return current + update


@dataclass
class FuncReducerState(StateSchema):
    counter: Annotated[int, my_reducer] = 0
    name: str = ""


class TestFunctionReducer:
    def test_function_reducer_applied(self):
        registry = FieldReducerRegistry.from_schema(FuncReducerState)
        assert registry.has_reducer("counter")

    def test_function_reducer_accumulate(self):
        state = FuncReducerState(counter=5)
        state.reduce_update({"counter": 3})
        assert state.counter == 8

    def test_function_reducer_name_unchanged(self):
        state = FuncReducerState(name="alice")
        state.reduce_update({"name": "bob"})
        assert state.name == "bob"
