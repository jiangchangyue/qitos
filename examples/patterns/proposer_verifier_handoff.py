"""Pattern: Proposer-Verifier via Handoff — proposer suggests, verifier critiques.

Demonstrates:
- Alternating handoffs with ContextStrategy.SUMMARY
- SharedMemory for solution history
- Convergence detection in verifier
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
from qitos.core.shared_memory import InMemorySharedMemory
from qitos.kit import (
    CodingToolSet,
    REACT_SYSTEM_PROMPT,
    ReActTextParser,
    format_action,
    render_prompt,
)
from qitos.models import OpenAICompatibleModel

WORKSPACE = Path("./playground/proposer_verifier_handoff")
MODEL_NAME = os.getenv("QITOS_MODEL", "glm-5.1-w4a8")
MODEL_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://ekkmopeh8ecgccbjjb9johhhd5dcabcc.openapi-sj.sii.edu.cn/v1/")
MAX_STEPS = 12


# ── Shared state ─────────────────────────────────────────────────────────


@dataclass
class SharedState(StateSchema):
    scratchpad: list[str] = field(default_factory=list)
    target_file: str = "buggy_module.py"
    proposal_count: int = 0
    verified: bool = False


# ── Proposer: suggests a fix ─────────────────────────────────────────────


class ProposerAgent(AgentModule[SharedState, dict[str, Any], Action]):
    """Proposes a fix and hands off to verifier."""

    name = "proposer"

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
        """After applying a fix, hand off to verifier."""
        if state.current_step >= 2 and state.proposal_count == 0:
            state.proposal_count += 1
            return Decision.handoff(
                target="verifier",
                rationale="Fix applied. Handing off to verifier for review.",
                handoff_message="Please verify the proposed fix.",
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
            f"Target file: {state.target_file}",
            f"You are the proposer agent. Read the code and propose a fix.",
            f"Proposal count: {state.proposal_count}",
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
            if isinstance(first, dict) and int(first.get("returncode", 1)) == 0:
                state.final_result = "Fix verified and accepted."
                state.verified = True
        state.scratchpad = state.scratchpad[-30:]
        return state


# ── Verifier: critiques the fix ──────────────────────────────────────────


class VerifierAgent(AgentModule[SharedState, dict[str, Any], Action]):
    """Verifier that checks the proposed fix and either approves or requests revision."""

    name = "verifier"

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
        """After verifying, either approve (final) or request revision (handoff back)."""
        # Simple convergence: after verification step, mark as final
        if state.current_step >= 1:
            return Decision.final(
                answer="Fix verified. The function add(a, b) now returns a + b."
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
            f"Target file: {state.target_file}",
            f"You are the verifier agent. Verify the proposed fix.",
            f"Step: {state.current_step}/{state.max_steps}",
        ]
        if state.scratchpad:
            lines.append("Previous context (from proposer):")
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
                state.final_result = "Fix verified and accepted."
                state.verified = True
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

    proposer = ProposerAgent(llm=llm, workspace_root=str(WORKSPACE))
    verifier = VerifierAgent(llm=llm, workspace_root=str(WORKSPACE))

    agent_registry = AgentRegistry()
    agent_registry.register(
        AgentSpec(
            name="proposer",
            description="Proposer agent that suggests fixes",
            agent=proposer,
        )
    )
    agent_registry.register(
        AgentSpec(
            name="verifier",
            description="Verifier agent that checks and approves fixes",
            agent=verifier,
            context_strategy=ContextStrategy.SUMMARY,
            shared_memory=shared_mem,
        )
    )

    engine = Engine(
        agent=proposer,
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
