"""CyberGym benchmark scorer."""

from __future__ import annotations

from typing import Any, Dict

from qitos.core import BenchmarkRunResult, ExperimentSpec, RunSpec

from ..contracts import BenchmarkScorer, PreparedBenchmarkTask


class CyberGymScorer(BenchmarkScorer):
    """Keep the normalized result and attach CyberGym-specific metadata."""

    def score(
        self,
        *,
        prepared: PreparedBenchmarkTask,
        run_spec: RunSpec,
        experiment_spec: ExperimentSpec,
        execution: Any,
        evaluation: Dict[str, Any],
        base_result: BenchmarkRunResult,
    ) -> BenchmarkRunResult:
        _ = (run_spec, experiment_spec, execution)
        base_result.metadata = {
            **dict(base_result.metadata or {}),
            "benchmark_runtime": dict(prepared.runtime_metadata or {}),
            "cybergym": dict(evaluation or {}),
            "family": "cybergym",
        }
        return base_result
