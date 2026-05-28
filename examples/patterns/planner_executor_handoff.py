"""Pattern: Planner-Executor via Handoff — planner creates a plan, executor carries it out.

Demonstrates:
- ContextStrategy.FULL so executor sees full planning history
- StateAdapter converts PlannerState → ExecutorState
- Return handoff via Decision.handoff(target="planner") for review
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
from qitos.core.agent_spec import StateAdapter
from qitos.kit import (
    CodingToolSet,
    REACT_SYSTEM_PROMPT,
    ReActTextParser,
    format_action,
    render_prompt,
)
from qitos.models import OpenAICompatibleModel

WORKSPACE = Path("./playground/planner_executor_handoff")
MODEL_NAME = os.getenv("QITOS_MODEL", "glm-5.1-w4a8")
MODEL_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://ekkmopeh8ecgccbjjb9johhhd5dcabcc.openapi-sj.sii.edu.cn/v1/")
MAX_STEPS = 10


# ── State types ──────────────────────────────────────────────────────────


@dataclass
class PlannerState(StateSchema):
    scratchpad: list[str] = field(default_factory=list)
    plan_steps: list[str] = field(default_factory=list)
    target_file: str = "buggy_module.py"


@dataclass
class ExecutorState(StateSchema):
    scratchpad: list[str] = field(default_factory=list)
    plan_steps: list[str] = field(default_factory=list)
    target_file: str = "buggy_module.py"
    current_plan_step: int = 0


class PlannerToExecutorAdapter(StateAdapter[PlannerState, ExecutorState]):
    """Convert PlannerState → ExecutorState for handoff."""

    def adapt(self, source: PlannerState) -> ExecutorState:
        return ExecutorState(
            task=source.task,
            max_steps=source.max_steps,
            plan_steps=list(source.plan_steps),
            target_file=source.target_file,
            current_plan_step=0,
        )


# ── Planner: creates a plan and hands off ────────────────────────────────


class PlannerAgent(AgentModule[PlannerState, dict[str, Any], Action]):
    """Planner that creates a step-by-step plan and delegates to executor."""

    name = "planner"

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

    def init_state(self, task: str, **kwargs: Any) -> PlannerState:
        return PlannerState(task=task, max_steps=int(kwargs.get("max_steps", MAX_STEPS)))

    def decide(self, state: PlannerState, observation: dict[str, Any]) -> Decision[Action] | None:
        """After inspecting, hand off to executor with the plan."""
        if state.current_step >= 1 and state.plan_steps:
            return Decision.handoff(
                target="executor",
                rationale="Plan created. Handing off to executor.",
                handoff_message="Execute the plan to fix the bug.",
            )
        return None

    def build_system_prompt(self, state: PlannerState) -> str | None:
        return render_prompt(
            REACT_SYSTEM_PROMPT,
            {"tool_schema": self.tool_registry.get_tool_descriptions()},
        )

    def prepare(self, state: PlannerState) -> str:
        lines = [
            f"Task: {state.task}",
            f"Your job: Read the code, create a plan, then hand off to the executor.",
            f"Step: {state.current_step}/{state.max_steps}",
        ]
        if state.scratchpad:
            lines.append("Recent trajectory:")
            lines.extend(state.scratchpad[-8:])
        return "\n".join(lines)

    def reduce(
        self,
        state: PlannerState,
        observation: dict[str, Any],
        decision: Decision[Action],
    ) -> PlannerState:
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
            # Extract plan from observations
            if isinstance(first, dict) and "output" in first:
                content = str(first["output"])
                if "plan" in content.lower():
                    state.plan_steps.append(content[:200])
        state.scratchpad = state.scratchpad[-30:]
        # Default plan if not extracted
        if not state.plan_steps and state.current_step >= 1:
            state.plan_steps = [
                "Read the buggy file",
                "Fix add() to return a + b instead of a - b",
                "Run verification",
            ]
        return state


# ── Executor: carries out the plan ───────────────────────────────────────


class ExecutorAgent(AgentModule[ExecutorState, dict[str, Any], Action]):
    """Executor that carries out the plan created by the planner."""

    name = "executor"

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

    def init_state(self, task: str, **kwargs: Any) -> ExecutorState:
        return ExecutorState(task=task, max_steps=int(kwargs.get("max_steps", MAX_STEPS)))

    def build_system_prompt(self, state: ExecutorState) -> str | None:
        return render_prompt(
            REACT_SYSTEM_PROMPT,
            {"tool_schema": self.tool_registry.get_tool_descriptions()},
        )

    def prepare(self, state: ExecutorState) -> str:
        lines = [
            f"Task: {state.task}",
            f"Target file: {state.target_file}",
            f"You are the executor agent. Follow the plan and apply fixes.",
        ]
        if state.plan_steps:
            lines.append("Plan:")
            for i, step in enumerate(state.plan_steps, 1):
                lines.append(f"  {i}. {step}")
            lines.append(f"Current step: {state.current_plan_step + 1}")
        lines.append(f"Step: {state.current_step}/{state.max_steps}")
        return "\n".join(lines)

    def reduce(
        self,
        state: ExecutorState,
        observation: dict[str, Any],
        decision: Decision[Action],
    ) -> ExecutorState:
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
                state.final_result = "Plan executed. Fix applied and verified."
                state.current_plan_step = len(state.plan_steps)
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

    planner = PlannerAgent(llm=llm, workspace_root=str(WORKSPACE))
    executor = ExecutorAgent(llm=llm, workspace_root=str(WORKSPACE))

    agent_registry = AgentRegistry()
    agent_registry.register(
        AgentSpec(
            name="planner",
            description="Planner agent that inspects code and creates plans",
            agent=planner,
        )
    )
    agent_registry.register(
        AgentSpec(
            name="executor",
            description="Executor agent that carries out plans",
            agent=executor,
            context_strategy=ContextStrategy.FULL,
            state_adapter=PlannerToExecutorAdapter(),
        )
    )

    engine = Engine(
        agent=planner,
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
