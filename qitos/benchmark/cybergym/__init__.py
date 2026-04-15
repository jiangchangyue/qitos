"""CyberGym benchmark integration."""

from __future__ import annotations

import importlib

_LAZY_ATTRS = {
    "CyberGymBenchmarkAdapter": (".adapter", "CyberGymBenchmarkAdapter"),
    "load_cybergym_tasks": (".adapter", "load_cybergym_tasks"),
    "task_slug": (".adapter", "task_slug"),
    "CyberGymEvaluator": (".evaluator", "CyberGymEvaluator"),
    "CyberGymRuntimeHook": (".runtime", "CyberGymRuntimeHook"),
    "prepare_task_dir": (".runtime", "prepare_task_dir"),
    "CyberGymScorer": (".scorer", "CyberGymScorer"),
    "make_trace_writer": (".runner", "make_trace_writer"),
    "run_cybergym_agent_task": (".runner", "run_cybergym_agent_task"),
    "run_cybergym_task": (".runner", "run_cybergym_task"),
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
    "CyberGymBenchmarkAdapter",
    "CyberGymEvaluator",
    "CyberGymRuntimeHook",
    "CyberGymScorer",
    "load_cybergym_tasks",
    "make_trace_writer",
    "prepare_task_dir",
    "run_cybergym_agent_task",
    "run_cybergym_task",
    "task_slug",
]
