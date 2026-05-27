"""Reflexion single-agent template — act, evaluate, reflect, retry with memory.

Provides configuration for the Reflexion pattern where:
- An agent takes actions toward a task
- On failure, a verbal reflection is generated
- Reflections are stored and injected into future prompts
- The agent retries, learning from past mistakes

Usage:
    from templates.reflexion.agent import ReflexionConfig
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class ReflexionConfig:
    """Configuration for the Reflexion pattern."""

    agent_name: str = "reflexion_agent"
    max_reflections: int = 3
    success_threshold: float = 0.6
    max_steps: int = 15


def build_reflexion_registry(config: ReflexionConfig) -> dict:
    """Build configuration dict for the Reflexion pattern.

    Returns:
        Configuration dict for use with ReflexionAgent.
    """
    return {
        "max_reflections": config.max_reflections,
        "success_threshold": config.success_threshold,
        "max_steps": config.max_steps,
    }
