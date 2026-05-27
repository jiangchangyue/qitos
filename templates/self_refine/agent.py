"""Self-Refine single-agent template — generate, critique, refine loop.

Provides configuration for the Self-Refine pattern where:
- An agent generates an initial draft
- A critic evaluates draft quality
- The agent refines the draft based on critique
- The loop continues until quality threshold is met

Usage:
    from templates.self_refine.agent import SelfRefineConfig
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class SelfRefineConfig:
    """Configuration for the Self-Refine pattern."""

    agent_name: str = "self_refiner"
    max_refinements: int = 3
    quality_threshold: float = 0.7
    max_steps: int = 10


def build_self_refine_registry(config: SelfRefineConfig) -> dict:
    """Build configuration dict for the Self-Refine pattern.

    Returns:
        Configuration dict for use with SelfRefineAgent.
    """
    return {
        "max_refinements": config.max_refinements,
        "quality_threshold": config.quality_threshold,
        "max_steps": config.max_steps,
    }
