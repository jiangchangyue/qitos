"""Model-profile inference for protocol selection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional


@dataclass(frozen=True)
class ModelProfile:
    id: str
    model_matchers: tuple[str, ...]
    default_protocol: str
    fallback_protocols: tuple[str, ...] = field(default_factory=tuple)
    tool_schema_style: str = "react"
    notes: str = ""


_PROFILES: tuple[ModelProfile, ...] = (
    ModelProfile(
        id="minimax_default",
        model_matchers=("minimax-", "minimax/", "m2.5", "abab"),
        default_protocol="minimax_tool_call_v1",
        fallback_protocols=("terminus_xml_v1", "terminus_json_v1", "json_decision_v1"),
        tool_schema_style="minimax",
        notes="MiniMax models commonly emit native XML-like tool call markup.",
    ),
    ModelProfile(
        id="openai_json",
        model_matchers=("gpt-4.1", "gpt-4o", "o3", "o4-mini", "chatgpt-4o"),
        default_protocol="json_decision_v1",
        fallback_protocols=("react_text_v1",),
        tool_schema_style="json",
    ),
    ModelProfile(
        id="anthropic_react",
        model_matchers=("claude-",),
        default_protocol="react_text_v1",
        fallback_protocols=("json_decision_v1",),
        tool_schema_style="react",
    ),
    ModelProfile(
        id="gemini_xml",
        model_matchers=("gemini-",),
        default_protocol="xml_decision_v1",
        fallback_protocols=("json_decision_v1", "react_text_v1"),
        tool_schema_style="xml",
    ),
    ModelProfile(
        id="qwen_json",
        model_matchers=("qwen",),
        default_protocol="json_decision_v1",
        fallback_protocols=("xml_decision_v1", "react_text_v1"),
        tool_schema_style="json",
    ),
)


def _normalize(model_name: Optional[str]) -> str:
    return str(model_name or "").strip().lower()


def infer_model_profile(model_name: Optional[str]) -> Optional[ModelProfile]:
    normalized = _normalize(model_name)
    if not normalized:
        return None
    for profile in _PROFILES:
        if any(
            normalized.startswith(prefix) or prefix in normalized
            for prefix in profile.model_matchers
        ):
            return profile
    return None


def infer_default_protocol(
    model_name: Optional[str], *, fallback: str = "react_text_v1"
) -> str:
    profile = infer_model_profile(model_name)
    if profile is None:
        return fallback
    return profile.default_protocol


def known_model_profiles() -> Iterable[ModelProfile]:
    return _PROFILES


__all__ = [
    "ModelProfile",
    "infer_model_profile",
    "infer_default_protocol",
    "known_model_profiles",
]
