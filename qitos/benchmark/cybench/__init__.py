"""CyBench benchmark integration."""

from __future__ import annotations

import importlib

_PKG_NAME = "cybench"

_LAZY_ATTRS = {
    "CyBenchAdapter": (".adapter", "CyBenchAdapter"),
    "load_cybench_tasks": (".adapter", "load_cybench_tasks"),
    "CyBenchEvaluatorBridge": (".evaluator", "CyBenchEvaluatorBridge"),
    "run_cybench_task": (".runner", "run_cybench_task"),
    "CyBenchRuntime": (".runtime", "CyBenchRuntime"),
    "CyBenchRuntimeHook": (".runtime", "CyBenchRuntimeHook"),
    "score_cybench_submission": (".runtime", "score_cybench_submission"),
    "CyBenchScorer": (".scorer", "CyBenchScorer"),
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
    "CyBenchAdapter",
    "CyBenchEvaluatorBridge",
    "CyBenchRuntimeHook",
    "CyBenchScorer",
    "load_cybench_tasks",
    "run_cybench_task",
    "CyBenchRuntime",
    "score_cybench_submission",
]
