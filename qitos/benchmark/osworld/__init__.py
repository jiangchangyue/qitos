"""OSWorld benchmark adapter, runtime, evaluator, and scorer."""

import warnings

warnings.warn(
    "qitos.benchmark.osworld is deprecated. Use qitos.recipes.benchmarks instead.",
    DeprecationWarning,
    stacklevel=2,
)

from .adapter import OSWorldBenchmarkAdapter, load_osworld_tasks
from .evaluator import OSWorldEvaluator, evaluate_task, resolve_eval_cache_dir
from .runner import run_osworld_task
from .runtime import OSWorldContainerLauncher, OSWorldRuntimeHook, run_setup_config
from .scorer import OSWorldScorer

__all__ = [
    "OSWorldBenchmarkAdapter",
    "OSWorldContainerLauncher",
    "OSWorldEvaluator",
    "OSWorldRuntimeHook",
    "OSWorldScorer",
    "evaluate_task",
    "load_osworld_tasks",
    "resolve_eval_cache_dir",
    "run_osworld_task",
    "run_setup_config",
]
