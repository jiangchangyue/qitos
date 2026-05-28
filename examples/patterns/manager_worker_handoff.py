"""Pattern: Manager-Worker via Handoff — manager delegates to specialist workers.

Demonstrates:
- ContextStrategy.SUMMARY with HandoffContext.payload for task briefing
- SharedMemory for progress tracking across agents
- Worker uses Decision.final() to return results
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from qitos import (
    Action,
    AgentModule,
    AgentRegistry,
    AgentSpec,
    ContextStrategy,
    Decision,
    Engine,
    StateSchema,
    ToolRegistry,
)
from qitos.core.agent_spec import HandoffContext
from qitos.core.shared_memory import InMemorySharedMemory
from qitos.kit import (
    CodingToolSet,
    REACT_SYSTEM_PROMPT,
    ReActTextParser,
    format_action,
    render_prompt,
)
from qitos.models import OpenAICompatibleModel

WORKSPACE = Path("./playground/manager_worker_handoff")
MODEL_NAME = os.getenv("QITOS_MODEL", "glm-5.1-w4a8")
MODEL_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://ekkmopeh8ecgccbjjb9johhhd5dcabcc.openapi-sj.sii.edu.cn/v1/")
MAX_STEPS = 10


# ── Shared state ─────────────────────────────────────────────────────────


@dataclass
class SharedState(StateSchema):
    scratchpad: list[str] = field(default_factory=list)
    target_file: str = "buggy_module.py"


# ── Manager: inspects task and hands off ─────────────────────────────────


class ManagerAgent(AgentModule[SharedState, dict[str, Any], Action]):
    """Manager that inspects the task and delegates to a specialist worker."""

    name = "manager"

    def __init__(self, llm: Any, workspace_root: str):
        registry = ToolRegistry()
        registry.include(
            CodingToolSet(
                workspace_root=workspace_root,
                include_notebook=False,
                enable_lsp=False,
                enable_tasks=False,
                enable_web=False,
                expose_modern_names=False,
            )
        )
        super().__init__(
            tool_registry=registry, llm=llm, model_parser=ReActTextParser()
        )

    def init_state(self, task: str, **kwargs: Any) -> SharedState:
        return SharedState(task=task, max_steps=int(kwargs.get("max_steps", MAX_STEPS)))

    def decide(self, state: SharedState, observation: dict[str, Any]) -> Decision[Action] | None:
        """After the first inspection step, hand off to the coder worker."""
        if state.current_step >= 1:
            return Decision.handoff(
                target="coder",
                rationale="Inspection complete. Delegating to coder.",
                handoff_message="Fix the bug in buggy_module.py so that add(20, 22) returns 42.",
                handoff_memory_keys=["progress", "findings"],
            )
        return None

    def build_system_prompt(self, state: SharedState) -> str | None:
        return render_prompt(
            REACT_SYSTEM_PROMPT,
            {"tool_schema": self.tool_registry.get_tool_descriptions()},
        )

    def prepare(self, state: SharedState) -> str:
        lines = [
            f"Task: {state.task}",
            f"Your job: Inspect the code, then hand off to the coder agent.",
            f"Step: {state.current_step}/{state.max_steps}",
        ]
        if state.scratchpad:
            lines.append("Recent trajectory:")
            lines.extend(state.scratchpad[-8:])
        return "\n".join(lines)

    def reduce(
        self,
        state: SharedState,
        observation: dict[str, Any],
        decision: Decision[Action],
    ) -> SharedState:
        action_results = (
            observation.get("action_results", [])
            if isinstance(observation, dict)
            else []
        )
        if decision.rationale:
            state.scratchpad.append(f"Thought: {decision.rationale}")
        if decision.actions:
            state.scratchpad.append(f"Action: {format_action(decision.actions[0])}")
        if action_results:
            first = action_results[0]
            state.scratchpad.append(f"Observation: {first}")
        state.scratchpad = state.scratchpad[-30:]
        return state


# ── Worker: applies the fix ──────────────────────────────────────────────


class CoderWorker(AgentModule[SharedState, dict[str, Any], Action]):
    """Coder specialist that applies fixes and verifies."""

    name = "coder"

    def __init__(self, llm: Any, workspace_root: str):
        registry = ToolRegistry()
        registry.include(
            CodingToolSet(
                workspace_root=workspace_root,
                include_notebook=False,
                enable_lsp=False,
                enable_tasks=False,
                enable_web=False,
                expose_modern_names=False,
            )
        )
        super().__init__(
            tool_registry=registry, llm=llm, model_parser=ReActTextParser()
        )

    def init_state(self, task: str, **kwargs: Any) -> SharedState:
        return SharedState(task=task, max_steps=int(kwargs.get("max_steps", MAX_STEPS)))

    def build_system_prompt(self, state: SharedState) -> str | None:
        return render_prompt(
            REACT_SYSTEM_PROMPT,
            {"tool_schema": self.tool_registry.get_tool_descriptions()},
        )

    def prepare(self, state: SharedState) -> str:
        lines = [
            f"Task: {state.task}",
            f"Target file: {state.target_file}",
            f"You are the coder agent. Apply the fix and verify.",
            f"Step: {state.current_step}/{state.max_steps}",
        ]
        if state.scratchpad:
            lines.append("Previous context (from manager):")
            lines.extend(state.scratchpad[-8:])
        return "\n".join(lines)

    def reduce(
        self,
        state: SharedState,
        observation: dict[str, Any],
        decision: Decision[Action],
    ) -> SharedState:
        action_results = (
            observation.get("action_results", [])
            if isinstance(observation, dict)
            else []
        )
        if decision.rationale:
            state.scratchpad.append(f"Thought: {decision.rationale}")
        if decision.actions:
            state.scratchpad.append(f"Action: {format_action(decision.actions[0])}")
        if action_results:
            first = action_results[0]
            state.scratchpad.append(f"Observation: {first}")
            if isinstance(first, dict) and int(first.get("returncode", 1)) == 0:
                state.final_result = "Patch applied and verification passed."
        state.scratchpad = state.scratchpad[-30:]
        return state


# ── Main ─────────────────────────────────────────────────────────────────


def build_model() -> OpenAICompatibleModel:
    api_key = (os.getenv("OPENAI_API_KEY") or os.getenv("QITOS_API_KEY") or "").strip()
    if not api_key:
        raise ValueError(
            "Set OPENAI_API_KEY or QITOS_API_KEY before running this example."
        )
    return OpenAICompatibleModel(
        model=MODEL_NAME,
        api_key=api_key,
        base_url=MODEL_BASE_URL,
        temperature=0.2,
        max_tokens=2048,
    )


def main() -> None:
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    target = WORKSPACE / "buggy_module.py"
    if not target.exists():
        target.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")

    llm = build_model()
    shared_mem = InMemorySharedMemory()

    manager = ManagerAgent(llm=llm, workspace_root=str(WORKSPACE))
    coder = CoderWorker(llm=llm, workspace_root=str(WORKSPACE))

    agent_registry = AgentRegistry()
    agent_registry.register(
        AgentSpec(
            name="manager",
            description="Manager agent that inspects and delegates",
            agent=manager,
        )
    )
    agent_registry.register(
        AgentSpec(
            name="coder",
            description="Coder agent that applies fixes and verifies",
            agent=coder,
            context_strategy=ContextStrategy.SUMMARY,
            handoff_context=HandoffContext(
                strategy=ContextStrategy.SUMMARY,
                payload={"task_type": "bug_fix", "priority": "high"},
            ),
            shared_memory=shared_mem,
        )
    )

    engine = Engine(
        agent=manager,
        agent_registry=agent_registry,
        budget=None,
    )
    result = engine.run(
        "Find and fix the bug in buggy_module.py so that add(20, 22) returns 42.",
        workspace=str(WORKSPACE),
        max_steps=MAX_STEPS,
    )

    print("workspace:", WORKSPACE)
    print("final_result:", result.state.final_result)
    print("stop_reason:", result.state.stop_reason)


if __name__ == "__main__":
    main()
