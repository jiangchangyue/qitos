"""Thin CyberGym benchmark entrypoint backed by the canonical recipe."""

from qitos.recipes.benchmarks.cybergym import (
    main,
    run_cybergym_agent_task,
    run_cybergym_recipe_task,
)

__all__ = [
    "main",
    "run_cybergym_agent_task",
    "run_cybergym_recipe_task",
]


if __name__ == "__main__":
    raise SystemExit(main())
