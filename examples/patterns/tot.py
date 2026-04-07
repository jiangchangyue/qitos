"""Pattern: Tree-of-Thought with branch search over EPUB evidence."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from qitos import Action, AgentModule, Decision, StateSchema, ToolRegistry
from qitos.kit import DynamicTreeSearch, EpubToolSet, format_action
from qitos.models import OpenAICompatibleModel

TASK = "Read the EPUB and answer the question with concise supporting evidence."
WORKSPACE = Path("./playground/tot_pattern")
EPUB_PATH = WORKSPACE / "book.epub"
QUESTION = "What is the main argument of chapter 1?"
MODEL_NAME = os.getenv("QITOS_MODEL", "Qwen/Qwen3-8B")
MODEL_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1/")
MAX_STEPS = 12

THOUGHT_PROMPT = """Question: {question}
EPUB path: {epub_path}
Evidence:
{evidence}

Return JSON:
{{
  "thoughts": [{{"idea": "...", "score": 0.0, "action": {{"name": "epub.list_chapters|epub.search|epub.read_chapter", "args": {{...}}}}}}],
  "can_answer": true_or_false,
  "answer": "optional"
}}
"""


@dataclass
class ToTState(StateSchema):
    epub_path: str = "book.epub"
    question: str = ""
    evidence: list[str] = field(default_factory=list)
    scratchpad: list[str] = field(default_factory=list)


class ToTAgent(AgentModule[ToTState, dict[str, Any], Action]):
    def __init__(self, llm: Any, workspace_root: str):
        registry = ToolRegistry()
        registry.register_toolset(
            EpubToolSet(workspace_root=workspace_root), namespace="epub"
        )
        super().__init__(tool_registry=registry, llm=llm)

    def init_state(self, task: str, **kwargs: Any) -> ToTState:
        return ToTState(
            task=task,
            max_steps=int(kwargs.get("max_steps", MAX_STEPS)),
            epub_path=str(kwargs.get("epub_path", EPUB_PATH.name)),
            question=str(kwargs.get("question", QUESTION)),
        )

    def decide(self, state: ToTState, observation: dict[str, Any]):
        if state.current_step == 0:
            return Decision.act(
                [Action(name="epub.list_chapters", args={"path": state.epub_path})],
                rationale="bootstrap_catalog",
            )

        raw = self.llm(
            [
                {"role": "system", "content": "Return valid JSON only."},
                {
                    "role": "user",
                    "content": THOUGHT_PROMPT.format(
                        question=state.question,
                        epub_path=state.epub_path,
                        evidence=self._evidence_block(state),
                    ),
                },
            ]
        )
        parsed = self._parse_json(str(raw))
        if not parsed:
            return Decision.act(
                [
                    Action(
                        name="epub.search",
                        args={
                            "path": state.epub_path,
                            "query": state.question,
                            "top_k": 3,
                        },
                    )
                ],
                rationale="fallback_search",
            )

        if (
            bool(parsed.get("can_answer"))
            and str(parsed.get("answer", "")).strip()
            and len(state.evidence) >= 2
        ):
            return Decision.final(answer=str(parsed["answer"]))

        candidates: list[Decision[Action]] = []
        for item in parsed.get("thoughts", []):
            if not isinstance(item, dict):
                continue
            action = item.get("action") or {}
            name = str(action.get("name", "")).strip()
            args = action.get("args") or {}
            if not name or not isinstance(args, dict):
                continue
            args.setdefault("path", state.epub_path)
            score = float(item.get("score", 0.5))
            candidates.append(
                Decision.act(
                    [Action(name=name, args=args)],
                    rationale=str(item.get("idea", "candidate")),
                    meta={"score": score},
                )
            )

        if not candidates:
            return Decision.act(
                [
                    Action(
                        name="epub.search",
                        args={
                            "path": state.epub_path,
                            "query": state.question,
                            "top_k": 3,
                        },
                    )
                ],
                rationale="fallback_search",
            )
        return Decision.branch(candidates=candidates, rationale="tot_branch")

    def reduce(
        self, state: ToTState, observation: dict[str, Any], decision: Decision[Action]
    ) -> ToTState:
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
            result = action_results[0]
            state.scratchpad.append(f"Observation: {result}")
            if isinstance(result, dict):
                if isinstance(result.get("hits"), list):
                    for hit in result["hits"][:3]:
                        if isinstance(hit, dict):
                            state.evidence.append(str(hit.get("snippet", "")))
                if isinstance(result.get("content"), str):
                    state.evidence.append(result["content"][:320])
        state.evidence = state.evidence[-20:]
        state.scratchpad = state.scratchpad[-30:]
        return state

    def _evidence_block(self, state: ToTState) -> str:
        if not state.evidence:
            return "- none"
        return "\n".join(f"- {item}" for item in state.evidence[-8:])

    def _parse_json(self, raw: str) -> dict[str, Any] | None:
        text = raw.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except Exception:
            pass
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                return None
        return None


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
    if not EPUB_PATH.exists():
        raise FileNotFoundError(
            f"Expected an EPUB at {EPUB_PATH}. Place a sample book there before running this example."
        )

    agent = ToTAgent(llm=build_model(), workspace_root=str(WORKSPACE))
    result = agent.run(
        task=TASK,
        workspace=str(WORKSPACE),
        epub_path=EPUB_PATH.name,
        question=QUESTION,
        max_steps=MAX_STEPS,
        search=DynamicTreeSearch(top_k=2),
        return_state=True,
    )
    print("workspace:", WORKSPACE)
    print("final_result:", result.state.final_result)
    print("stop_reason:", result.state.stop_reason)


if __name__ == "__main__":
    main()
