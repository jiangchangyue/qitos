"""GAIA benchmark integration."""

from __future__ import annotations

import importlib

_PKG_NAME = "gaia"

_LAZY_ATTRS = {
    "GaiaAdapter": (".adapter", "GaiaAdapter"),
    "load_gaia_tasks": (".adapter", "load_gaia_tasks"),
    "GaiaEvaluator": (".evaluator", "GaiaEvaluator"),
    "run_gaia_task": (".runner", "run_gaia_task"),
    "GaiaRuntimeHook": (".runtime", "GaiaRuntimeHook"),
    "GaiaScorer": (".scorer", "GaiaScorer"),
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
    "GaiaAdapter",
    "GaiaEvaluator",
    "GaiaRuntimeHook",
    "GaiaScorer",
    "load_gaia_tasks",
    "run_gaia_task",
]
