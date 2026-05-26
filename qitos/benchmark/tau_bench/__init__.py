"""Tau-Bench benchmark integration."""

from __future__ import annotations

import importlib

_PKG_NAME = "tau_bench"

_LAZY_ATTRS = {
    "TauBenchAdapter": (".adapter", "TauBenchAdapter"),
    "load_tau_bench_tasks": (".adapter", "load_tau_bench_tasks"),
    "TauBenchEvaluator": (".evaluator", "TauBenchEvaluator"),
    "run_tau_bench_task": (".runner", "run_tau_bench_task"),
    "TauBenchRuntimeHook": (".runtime", "TauBenchRuntimeHook"),
    "TauRuntimeEnv": (".runtime", "TauRuntimeEnv"),
    "get_tau_runtime_env": (".runtime", "get_tau_runtime_env"),
    "TauBenchScorer": (".scorer", "TauBenchScorer"),
}


def __getattr__(name: str):
    target = _LAZY_ATTRS.get(name)
    if target is not None:
        import warnings

        warnings.warn(
            f"Importing {name!r} from qitos.benchmark.{_PKG_NAME} is deprecated. "
            f"Use qitos.recipes.benchmarks instead.",
            DeprecationWarning,
            stacklevel=2,
        )
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    module = importlib.import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


__all__ = [
    "TauBenchAdapter",
    "TauBenchEvaluator",
    "TauBenchRuntimeHook",
    "TauBenchScorer",
    "load_tau_bench_tasks",
    "run_tau_bench_task",
    "TauRuntimeEnv",
    "get_tau_runtime_env",
]
