"""Tests for stop criteria."""

from __future__ import annotations

from qitos.core.errors import StopReason
from qitos.engine.stop_criteria import (
    FinalResultCriteria,
    MaxRuntimeCriteria,
    MaxStepsCriteria,
    MaxTokensCriteria,
    StagnationCriteria,
)


class TestMaxTokensCriteria:
    def test_does_not_stop_when_under_budget(self):
        criteria = MaxTokensCriteria(max_tokens=1000)
        should_stop, reason, detail = criteria.should_stop(
            state=None, step_count=5, runtime_info={"total_tokens": 500}
        )
        assert should_stop is False
        assert reason is None
        assert detail is None

    def test_stops_when_at_budget(self):
        criteria = MaxTokensCriteria(max_tokens=1000)
        should_stop, reason, detail = criteria.should_stop(
            state=None, step_count=5, runtime_info={"total_tokens": 1000}
        )
        assert should_stop is True
        assert reason == StopReason.BUDGET_TOKENS
        assert "total_tokens=1000" in detail

    def test_stops_when_over_budget(self):
        criteria = MaxTokensCriteria(max_tokens=1000)
        should_stop, reason, detail = criteria.should_stop(
            state=None, step_count=5, runtime_info={"total_tokens": 1500}
        )
        assert should_stop is True
        assert reason == StopReason.BUDGET_TOKENS
        assert "total_tokens=1500" in detail

    def test_defaults_to_zero_when_no_runtime_info(self):
        criteria = MaxTokensCriteria(max_tokens=1000)
        should_stop, reason, detail = criteria.should_stop(
            state=None, step_count=5, runtime_info=None
        )
        assert should_stop is False

    def test_defaults_to_zero_when_no_total_tokens_key(self):
        criteria = MaxTokensCriteria(max_tokens=1000)
        should_stop, reason, detail = criteria.should_stop(
            state=None, step_count=5, runtime_info={"elapsed_seconds": 10.0}
        )
        assert should_stop is False


class TestMaxStepsCriteria:
    def test_stops_at_max_steps(self):
        criteria = MaxStepsCriteria(max_steps=10)
        should_stop, reason, detail = criteria.should_stop(
            state=None, step_count=10
        )
        assert should_stop is True
        assert reason == StopReason.BUDGET_STEPS

    def test_does_not_stop_before_max_steps(self):
        criteria = MaxStepsCriteria(max_steps=10)
        should_stop, reason, detail = criteria.should_stop(
            state=None, step_count=9
        )
        assert should_stop is False


class TestMaxRuntimeCriteria:
    def test_stops_when_time_exceeded(self):
        criteria = MaxRuntimeCriteria(max_runtime_seconds=30.0)
        should_stop, reason, detail = criteria.should_stop(
            state=None, step_count=5, runtime_info={"elapsed_seconds": 35.0}
        )
        assert should_stop is True
        assert reason == StopReason.BUDGET_TIME

    def test_does_not_stop_when_within_time(self):
        criteria = MaxRuntimeCriteria(max_runtime_seconds=30.0)
        should_stop, reason, detail = criteria.should_stop(
            state=None, step_count=5, runtime_info={"elapsed_seconds": 25.0}
        )
        assert should_stop is False
