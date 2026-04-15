"""Benchmark adapters and runner contracts for QitOS."""

from __future__ import annotations

import importlib

from .base import BenchmarkAdapter, BenchmarkSource
from .contracts import (
    BenchmarkEvaluator,
    BenchmarkRuntimeHook,
    BenchmarkScorer,
    PreparedBenchmarkTask,
)

_LAZY_ATTRS = {
    "build_experiment_spec": (".common", "build_experiment_spec"),
    "evaluate_benchmark_results": (".common", "evaluate_benchmark_results"),
    "read_benchmark_results": (".common", "read_benchmark_results"),
    "write_benchmark_results": (".common", "write_benchmark_results"),
    "load_benchmark_tasks": (".runner", "load_benchmark_tasks"),
    "normalize_benchmark_name": (".runner", "normalize_benchmark_name"),
    "resolve_builtin_runner": (".runner", "resolve_builtin_runner"),
    "resolve_runner": (".runner", "resolve_runner"),
    "run_benchmark_tasks": (".runner", "run_benchmark_tasks"),
    "DesktopStarterAdapter": (".desktop", "DesktopStarterAdapter"),
    "load_desktop_tasks": (".desktop", "load_desktop_tasks"),
    "run_desktop_starter_task": (".desktop", "run_desktop_starter_task"),
    "OSWorldBenchmarkAdapter": (".osworld", "OSWorldBenchmarkAdapter"),
    "OSWorldContainerLauncher": (".osworld", "OSWorldContainerLauncher"),
    "OSWorldEvaluator": (".osworld", "OSWorldEvaluator"),
    "OSWorldRuntimeHook": (".osworld", "OSWorldRuntimeHook"),
    "OSWorldScorer": (".osworld", "OSWorldScorer"),
    "load_osworld_tasks": (".osworld", "load_osworld_tasks"),
    "run_osworld_task": (".osworld", "run_osworld_task"),
    "CyBenchAdapter": (".cybench", "CyBenchAdapter"),
    "CyBenchEvaluatorBridge": (".cybench", "CyBenchEvaluatorBridge"),
    "CyBenchRuntime": (".cybench", "CyBenchRuntime"),
    "CyBenchRuntimeHook": (".cybench", "CyBenchRuntimeHook"),
    "CyBenchScorer": (".cybench", "CyBenchScorer"),
    "load_cybench_tasks": (".cybench", "load_cybench_tasks"),
    "run_cybench_task": (".cybench", "run_cybench_task"),
    "score_cybench_submission": (".cybench", "score_cybench_submission"),
    "CyberGymBenchmarkAdapter": (".cybergym", "CyberGymBenchmarkAdapter"),
    "CyberGymEvaluator": (".cybergym", "CyberGymEvaluator"),
    "CyberGymRuntimeHook": (".cybergym", "CyberGymRuntimeHook"),
    "CyberGymScorer": (".cybergym", "CyberGymScorer"),
    "load_cybergym_tasks": (".cybergym", "load_cybergym_tasks"),
    "run_cybergym_task": (".cybergym", "run_cybergym_task"),
    "GaiaAdapter": (".gaia", "GaiaAdapter"),
    "GaiaEvaluator": (".gaia", "GaiaEvaluator"),
    "GaiaRuntimeHook": (".gaia", "GaiaRuntimeHook"),
    "GaiaScorer": (".gaia", "GaiaScorer"),
    "load_gaia_tasks": (".gaia", "load_gaia_tasks"),
    "run_gaia_task": (".gaia", "run_gaia_task"),
    "TauBenchAdapter": (".tau_bench", "TauBenchAdapter"),
    "TauBenchEvaluator": (".tau_bench", "TauBenchEvaluator"),
    "TauBenchRuntimeHook": (".tau_bench", "TauBenchRuntimeHook"),
    "TauBenchScorer": (".tau_bench", "TauBenchScorer"),
    "load_tau_bench_tasks": (".tau_bench", "load_tau_bench_tasks"),
    "run_tau_bench_task": (".tau_bench", "run_tau_bench_task"),
}


def __getattr__(name: str):
    target = _LAZY_ATTRS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    module = importlib.import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


__all__ = [
    "BenchmarkAdapter",
    "BenchmarkSource",
    "BenchmarkRuntimeHook",
    "BenchmarkEvaluator",
    "BenchmarkScorer",
    "PreparedBenchmarkTask",
    "load_benchmark_tasks",
    "normalize_benchmark_name",
    "run_benchmark_tasks",
    "build_experiment_spec",
    "write_benchmark_results",
    "read_benchmark_results",
    "evaluate_benchmark_results",
    "resolve_builtin_runner",
    "resolve_runner",
    "DesktopStarterAdapter",
    "load_desktop_tasks",
    "run_desktop_starter_task",
    "OSWorldBenchmarkAdapter",
    "OSWorldContainerLauncher",
    "OSWorldEvaluator",
    "OSWorldRuntimeHook",
    "OSWorldScorer",
    "load_osworld_tasks",
    "run_osworld_task",
    "CyBenchAdapter",
    "CyBenchEvaluatorBridge",
    "CyBenchRuntime",
    "CyBenchRuntimeHook",
    "CyBenchScorer",
    "run_cybench_task",
    "score_cybench_submission",
    "load_cybench_tasks",
    "CyberGymBenchmarkAdapter",
    "CyberGymEvaluator",
    "CyberGymRuntimeHook",
    "CyberGymScorer",
    "load_cybergym_tasks",
    "run_cybergym_task",
    "GaiaAdapter",
    "GaiaEvaluator",
    "GaiaRuntimeHook",
    "GaiaScorer",
    "load_gaia_tasks",
    "run_gaia_task",
    "TauBenchAdapter",
    "TauBenchEvaluator",
    "TauBenchRuntimeHook",
    "TauBenchScorer",
    "load_tau_bench_tasks",
    "run_tau_bench_task",
]
