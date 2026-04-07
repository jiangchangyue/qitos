"""Pattern: Reflexion with grounded self-critique over retrieved evidence."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from qitos import Action, AgentModule, Decision, StateSchema, ToolRegistry
from qitos.kit import HTMLExtractText, HTTPGet
from qitos.models import OpenAICompatibleModel

TASK = "Summarize the article and revise the answer until the critique says it is grounded."
WORKSPACE = Path("./playground/reflexion_pattern")
TARGET_URL = "https://www.thepaper.cn/newsDetail_forward_32639776"
MODEL_NAME = os.getenv("QITOS_MODEL", "Qwen/Qwen3-8B")
MODEL_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1/")
MAX_STEPS = 12
MAX_REFLECTIONS = 2

REFLEXION_PROMPT = """You are a reflexion actor-critic.

Task: {task}
Source URL: {target_url}
Source text:
{text}

Current draft answer:
{draft}

Previous reflections:
{reflections}

Return valid JSON only:
{{
  "answer": "revised answer",
  "citations": [{{"source": "source_text", "quote": "exact supporting quote"}}],
  "critique": {{
    "missing": ["missing aspect 1", "..."],
    "superfluous": ["unnecessary claim 1", "..."],
    "grounding": ["claim X is/ is not grounded because ..."],
    "needs_revision": true_or_false
  }}
}}

Hard constraints:
- Critique must be grounded in source text and discuss evidence quality.
- Always provide at least 2 citations when possible.
- Explicitly list both missing and superfluous aspects.
- No markdown, no extra text, JSON only.
"""


@dataclass
class ReflexionState(StateSchema):
    target_url: str = TARGET_URL
    page_html: str = ""
    page_text: str = ""
    draft_answer: str = ""
    reflections: list[dict[str, Any]] = field(default_factory=list)
    max_reflections: int = MAX_REFLECTIONS


class ReflexionAgent(AgentModule[ReflexionState, dict[str, Any], Action]):
    def __init__(self, llm: Any):
        registry = ToolRegistry()
        registry.register(HTTPGet())
        registry.register(HTMLExtractText())
        super().__init__(tool_registry=registry, llm=llm)

    def init_state(self, task: str, **kwargs: Any) -> ReflexionState:
        return ReflexionState(
            task=task,
            max_steps=int(kwargs.get("max_steps", MAX_STEPS)),
            target_url=str(kwargs.get("target_url", TARGET_URL)),
            max_reflections=int(kwargs.get("max_reflections", MAX_REFLECTIONS)),
        )

    def decide(self, state: ReflexionState, observation: dict[str, Any]):
        if not state.page_html:
            return Decision.act(
                [Action(name="http_get", args={"url": state.target_url})],
                rationale="fetch_source",
            )
        if not state.page_text:
            return Decision.act(
                [
                    Action(
                        name="extract_web_text",
                        args={"html": state.page_html, "max_chars": 12000},
                    )
                ],
                rationale="extract_source_text",
            )

        payload = self._reflect(state)
        if payload is None:
            return Decision.final("Failed to produce valid reflexion JSON output.")

        critique = (
            payload.get("critique") if isinstance(payload.get("critique"), dict) else {}
        )
        needs_revision = bool(critique.get("needs_revision", False))
        answer = str(payload.get("answer", "")).strip()

        state.draft_answer = answer
        state.reflections.append(payload)

        if needs_revision and len(state.reflections) <= state.max_reflections:
            return Decision.wait(rationale="reflexion_revision_cycle")

        citations = (
            payload.get("citations")
            if isinstance(payload.get("citations"), list)
            else []
        )
        return Decision.final(answer=f"{answer}\n\nCitations: {citations}")

    def reduce(
        self,
        state: ReflexionState,
        observation: dict[str, Any],
        decision: Decision[Action],
    ) -> ReflexionState:
        action_results = (
            observation.get("action_results", [])
            if isinstance(observation, dict)
            else []
        )
        if action_results:
            first = action_results[0]
            if isinstance(first, dict):
                if decision.actions and decision.actions[0].name == "http_get":
                    state.page_html = str(first.get("content", ""))
                if decision.actions and decision.actions[0].name == "extract_web_text":
                    state.page_text = str(first.get("content", ""))
        return state

    def _reflect(self, state: ReflexionState) -> dict[str, Any] | None:
        raw = self.llm(
            [
                {"role": "system", "content": "Return valid JSON only."},
                {
                    "role": "user",
                    "content": REFLEXION_PROMPT.format(
                        task=state.task,
                        target_url=state.target_url,
                        text=state.page_text[:9000],
                        draft=state.draft_answer or "<empty>",
                        reflections=json.dumps(
                            state.reflections[-2:], ensure_ascii=False
                        ),
                    ),
                },
            ]
        )
        text = str(raw).strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except Exception:
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
    agent = ReflexionAgent(llm=build_model())
    result = agent.run(
        task=TASK,
        workspace=str(WORKSPACE),
        target_url=TARGET_URL,
        max_steps=MAX_STEPS,
        max_reflections=MAX_REFLECTIONS,
        return_state=True,
    )
    print("workspace:", WORKSPACE)
    print("final_result:", result.state.final_result)
    print("reflections:", len(result.state.reflections))
    print("stop_reason:", result.state.stop_reason)


if __name__ == "__main__":
    main()
