"""CyberGym benchmark evaluator."""

from __future__ import annotations

from typing import Any, Dict

from qitos.core import ExperimentSpec, RunSpec

from ..contracts import BenchmarkEvaluator, PreparedBenchmarkTask


class CyberGymEvaluator(BenchmarkEvaluator):
    """Return CyberGym-native execution details for scoring."""

    def evaluate(
        self,
        *,
        prepared: PreparedBenchmarkTask,
        run_spec: RunSpec,
        experiment_spec: ExperimentSpec,
        execution: Any,
    ) -> Dict[str, Any]:
        _ = (prepared, run_spec, experiment_spec)
        if isinstance(execution, dict):
            return dict(execution)
        if hasattr(execution, "to_dict"):
            return dict(execution.to_dict())
        return {"execution": execution}
