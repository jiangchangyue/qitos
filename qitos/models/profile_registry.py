"""Model-profile inference for protocol selection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional

from ..harness._presets import known_family_presets


@dataclass(frozen=True)
class ModelProfile:
    id: str
    model_matchers: tuple[str, ...]
    default_protocol: str
    fallback_protocols: tuple[str, ...] = field(default_factory=tuple)
    tool_schema_style: str = "react"
    notes: str = ""


@dataclass(frozen=True)
class MultimodalCapabilityProfile:
    """Describes what visual inputs a model supports for multimodal observation adaptation."""

    model_name: str
    supports_screenshot: bool = True
    supports_dom: bool = True
    preferred_observation_mode: str = "screenshot_first"  # screenshot_first | dom_first | text_only
    max_visual_inputs: int = 4

    def adapt_observation(self, observation_pack: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt an ObservationPack dict based on model capabilities.

        Returns a modified observation pack suitable for this model.
        """
        pack = dict(observation_pack) if isinstance(observation_pack, dict) else {}

        if not self.supports_screenshot:
            # Remove screenshot, rely on DOM + OCR text
            pack.pop("screenshot", None)
            if not self.supports_dom:
                # Text-only: extract OCR text as the primary observation
                ocr_spans = pack.get("ocr", [])
                if isinstance(ocr_spans, list):
                    text_parts = [str(s.get("text", "")) for s in ocr_spans if isinstance(s, dict)]
                    pack["text"] = pack.get("text", "") + "\n" + " ".join(text_parts)
                pack.pop("dom", None)
                pack.pop("accessibility_tree", None)
                pack.pop("ui_candidates", None)

        return pack


# Known multimodal capability profiles for popular model families
_MULTIMODAL_PROFILES: Dict[str, MultimodalCapabilityProfile] = {
    "gpt-4o": MultimodalCapabilityProfile(
        model_name="gpt-4o",
        supports_screenshot=True,
        supports_dom=True,
        preferred_observation_mode="screenshot_first",
        max_visual_inputs=4,
    ),
    "gpt-4-turbo": MultimodalCapabilityProfile(
        model_name="gpt-4-turbo",
        supports_screenshot=True,
        supports_dom=True,
        preferred_observation_mode="screenshot_first",
        max_visual_inputs=1,
    ),
    "claude-3": MultimodalCapabilityProfile(
        model_name="claude-3",
        supports_screenshot=True,
        supports_dom=True,
        preferred_observation_mode="screenshot_first",
        max_visual_inputs=4,
    ),
    "qwen-vl": MultimodalCapabilityProfile(
        model_name="qwen-vl",
        supports_screenshot=True,
        supports_dom=True,
        preferred_observation_mode="screenshot_first",
        max_visual_inputs=5,
    ),
    "text-only": MultimodalCapabilityProfile(
        model_name="text-only",
        supports_screenshot=False,
        supports_dom=True,
        preferred_observation_mode="dom_first",
        max_visual_inputs=0,
    ),
}


def infer_multimodal_capability(model_name: Optional[str]) -> MultimodalCapabilityProfile:
    """Infer multimodal capability profile from model name.

    Falls back to a text-only profile for unknown models.
    """
    normalized = _normalize(model_name)
    if not normalized:
        return _MULTIMODAL_PROFILES["text-only"]

    # Check known profile keys
    for key, profile in _MULTIMODAL_PROFILES.items():
        if key in normalized or normalized.startswith(key):
            return profile

    # Heuristic: models with "vl", "vision", "visual" in name likely support screenshots
    vision_indicators = ("vl", "vision", "visual", "multimodal", "gpt-4o", "gpt-4-turbo", "claude-3", "gemini")
    if any(ind in normalized for ind in vision_indicators):
        return MultimodalCapabilityProfile(
            model_name=model_name or "",
            supports_screenshot=True,
            supports_dom=True,
            preferred_observation_mode="screenshot_first",
            max_visual_inputs=4,
        )

    # Default: text-only for unknown text models
    return _MULTIMODAL_PROFILES["text-only"]


def _tool_schema_style(default_protocol: str) -> str:
    value = str(default_protocol or "").strip().lower()
    if value == "minimax_tool_call_v1":
        return "minimax"
    if "xml" in value:
        return "xml"
    if "json" in value:
        return "json"
    return "react"


def _build_profiles() -> tuple[ModelProfile, ...]:
    profiles = []
    for preset in known_family_presets():
        profiles.append(
            ModelProfile(
                id=f"{preset.id}_default",
                model_matchers=tuple(preset.model_matchers),
                default_protocol=preset.default_protocol,
                fallback_protocols=tuple(preset.fallback_protocols),
                tool_schema_style=_tool_schema_style(preset.default_protocol),
                notes=preset.notes,
            )
        )
    return tuple(profiles)


_PROFILES: tuple[ModelProfile, ...] = _build_profiles()


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
    "MultimodalCapabilityProfile",
    "infer_model_profile",
    "infer_default_protocol",
    "infer_multimodal_capability",
    "known_model_profiles",
]
