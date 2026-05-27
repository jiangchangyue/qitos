"""Tests for MultimodalCapabilityProfile and multimodal observation fallback."""

from __future__ import annotations

import pytest

from qitos.models.profile_registry import (
    MultimodalCapabilityProfile,
    infer_multimodal_capability,
)


class TestMultimodalCapabilityProfile:
    def test_default_profile_supports_screenshot(self):
        p = MultimodalCapabilityProfile(model_name="test")
        assert p.supports_screenshot is True
        assert p.supports_dom is True
        assert p.preferred_observation_mode == "screenshot_first"

    def test_adapt_observation_screenshot_model(self):
        p = MultimodalCapabilityProfile(
            model_name="gpt-4o",
            supports_screenshot=True,
            supports_dom=True,
        )
        pack = {
            "text": "hello",
            "screenshot": {"path": "/tmp/shot.png"},
            "dom": "<html></html>",
            "ocr": [{"text": "button", "x": 10, "y": 20}],
        }
        result = p.adapt_observation(pack)
        assert "screenshot" in result
        assert "dom" in result

    def test_adapt_observation_text_only_model(self):
        p = MultimodalCapabilityProfile(
            model_name="text-model",
            supports_screenshot=False,
            supports_dom=False,
            preferred_observation_mode="text_only",
        )
        pack = {
            "text": "hello",
            "screenshot": {"path": "/tmp/shot.png"},
            "dom": "<html></html>",
            "ocr": [{"text": "button", "x": 10, "y": 20}],
        }
        result = p.adapt_observation(pack)
        assert "screenshot" not in result
        assert "dom" not in result
        assert "button" in result.get("text", "")

    def test_adapt_observation_dom_only_model(self):
        p = MultimodalCapabilityProfile(
            model_name="dom-model",
            supports_screenshot=False,
            supports_dom=True,
            preferred_observation_mode="dom_first",
        )
        pack = {
            "text": "hello",
            "screenshot": {"path": "/tmp/shot.png"},
            "dom": "<html></html>",
        }
        result = p.adapt_observation(pack)
        assert "screenshot" not in result
        assert "dom" in result


class TestInferMultimodalCapability:
    def test_gpt4o_detected(self):
        p = infer_multimodal_capability("gpt-4o-2024-05-13")
        assert p.supports_screenshot is True

    def test_claude3_detected(self):
        p = infer_multimodal_capability("claude-3-5-sonnet")
        assert p.supports_screenshot is True

    def test_qwen_vl_detected(self):
        p = infer_multimodal_capability("Qwen/Qwen2-VL-7B")
        assert p.supports_screenshot is True

    def test_text_model_fallback(self):
        p = infer_multimodal_capability("meta-llama/Llama-3-8B")
        assert p.supports_screenshot is False
        assert p.preferred_observation_mode == "dom_first"

    def test_none_returns_text_only(self):
        p = infer_multimodal_capability(None)
        assert p.supports_screenshot is False

    def test_empty_returns_text_only(self):
        p = infer_multimodal_capability("")
        assert p.supports_screenshot is False

    def test_vision_in_name_detected(self):
        p = infer_multimodal_capability("some-vision-model")
        assert p.supports_screenshot is True
