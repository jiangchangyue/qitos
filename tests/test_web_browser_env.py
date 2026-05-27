"""Tests for qitos.kit.env.web — WebBrowserEnv, providers, actions."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from qitos.kit.env.web import MockBrowserProvider, WebBrowserEnv
from qitos.kit.env.web.actions import (
    ALL_WEB_GUI_ACTIONS,
    WEB_ACTION_NAMES,
    web_action_space,
    validate_web_gui_action,
)
from qitos.kit.env.web.providers import WebBrowserProvider


# ---- helpers ----

_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x04\x00\x00\x00\xb5\x1c\x0c\x02\x00\x00\x00\x0bIDATx\xdac\xfc"
    b"\xff\x1f\x00\x02\xeb\x01\xf5i\xf6\x81\xb7\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _make_mock_screenshot(tmp: Path) -> str:
    p = tmp / "mock_screen.png"
    p.write_bytes(_PNG_BYTES)
    return str(p)


# ---- Action space ----

class TestWebActionSpace:
    def test_web_action_space_includes_desktop_actions(self):
        space = web_action_space()
        for action in ("click", "type_text", "scroll", "hotkey", "done"):
            assert action in space.allowed_actions

    def test_web_action_space_includes_web_actions(self):
        space = web_action_space()
        for action in WEB_ACTION_NAMES:
            assert action in space.allowed_actions

    def test_web_action_space_id(self):
        assert web_action_space().id == "web_browser_v1"

    def test_validate_navigate(self):
        result = validate_web_gui_action({"action_type": "navigate", "url": "https://example.com"})
        assert result.get("ok", False), f"navigate should be valid: {result}"

    def test_validate_go_back(self):
        result = validate_web_gui_action({"action_type": "go_back"})
        assert result.get("ok", False), f"go_back should be valid: {result}"

    def test_validate_click_still_works(self):
        result = validate_web_gui_action({"action_type": "click", "x": 100, "y": 200})
        assert result.get("ok", False), f"click should still be valid: {result}"

    def test_all_web_gui_actions_list(self):
        for action in ALL_WEB_GUI_ACTIONS:
            assert isinstance(action, str) and action


# ---- MockBrowserProvider ----

class TestMockBrowserProvider:
    def test_start_stop(self, tmp_path):
        provider = MockBrowserProvider(screenshot_path=_make_mock_screenshot(tmp_path))
        provider.start()
        assert provider.started
        provider.stop()
        assert not provider.started

    def test_capture_state_shape(self, tmp_path):
        provider = MockBrowserProvider(
            screenshot_path=_make_mock_screenshot(tmp_path),
            instruction="Search for cats",
            url="https://example.com",
        )
        provider.start()
        state = provider.capture_state()
        assert "screenshot" in state
        assert "dom" in state
        assert "accessibility_tree" in state
        assert "url" in state
        assert state["url"] == "https://example.com"
        provider.stop()

    def test_execute_navigate(self, tmp_path):
        provider = MockBrowserProvider(
            screenshot_path=_make_mock_screenshot(tmp_path),
            url="about:blank",
        )
        provider.start()
        result = provider.execute_action({"action_type": "navigate", "url": "https://google.com"})
        assert result["status"] == "success"
        assert provider.url == "https://google.com"
        provider.stop()

    def test_execute_go_back(self, tmp_path):
        provider = MockBrowserProvider(
            screenshot_path=_make_mock_screenshot(tmp_path),
            url="https://example.com",
        )
        provider.start()
        provider.execute_action({"action_type": "navigate", "url": "https://google.com"})
        result = provider.execute_action({"action_type": "go_back"})
        assert result["status"] == "success"
        assert provider.url == "https://example.com"
        provider.stop()

    def test_execute_desktop_action(self, tmp_path):
        provider = MockBrowserProvider(screenshot_path=_make_mock_screenshot(tmp_path))
        provider.start()
        result = provider.execute_action({"action_type": "click", "x": 100, "y": 200})
        assert result["status"] == "success"
        assert len(provider.actions) == 1
        provider.stop()

    def test_actions_recorded(self, tmp_path):
        provider = MockBrowserProvider(screenshot_path=_make_mock_screenshot(tmp_path))
        provider.start()
        provider.execute_action({"action_type": "click", "x": 10, "y": 20})
        provider.execute_action({"action_type": "type_text", "text": "hello"})
        assert len(provider.actions) == 2
        provider.stop()


# ---- WebBrowserEnv ----

class TestWebBrowserEnv:
    def test_from_mock(self, tmp_path):
        env = WebBrowserEnv.from_mock(
            screenshot_path=_make_mock_screenshot(tmp_path),
            instruction="Search for QitOS",
            url="https://example.com",
        )
        assert env.name == "web_browser_env"

    def test_setup_observe(self, tmp_path):
        env = WebBrowserEnv.from_mock(
            screenshot_path=_make_mock_screenshot(tmp_path),
            instruction="Test",
        )
        env.setup()
        obs = env.observe()
        assert obs.data is not None
        assert "multimodal" in obs.data
        assert "web" in obs.data
        env.close()

    def test_reset(self, tmp_path):
        env = WebBrowserEnv.from_mock(
            screenshot_path=_make_mock_screenshot(tmp_path),
            url="https://example.com",
        )
        env.setup()
        obs = env.reset(start_url="https://google.com")
        assert obs.data is not None
        env.close()

    def test_capabilities(self, tmp_path):
        env = WebBrowserEnv.from_mock(screenshot_path=_make_mock_screenshot(tmp_path))
        env.setup()
        caps = env.capabilities()
        assert caps["gui_observer"] is True
        assert caps["gui_controller"] is True
        assert caps["web_browser"] is True
        env.close()

    def test_action_space(self, tmp_path):
        env = WebBrowserEnv.from_mock(screenshot_path=_make_mock_screenshot(tmp_path))
        space = env.action_space()
        assert space.id == "web_browser_v1"
        assert "navigate" in space.allowed_actions
        assert "click" in space.allowed_actions

    def test_step_click(self, tmp_path):
        env = WebBrowserEnv.from_mock(screenshot_path=_make_mock_screenshot(tmp_path))
        env.setup()
        result = env.step({
            "actions": [{"action_type": "click", "x": 100, "y": 200}]
        })
        assert result.observation is not None
        assert not result.done
        env.close()

    def test_step_navigate(self, tmp_path):
        env = WebBrowserEnv.from_mock(screenshot_path=_make_mock_screenshot(tmp_path))
        env.setup()
        result = env.step({
            "actions": [{"action_type": "navigate", "url": "https://example.com"}]
        })
        assert result.observation is not None
        env.close()

    def test_step_done_action(self, tmp_path):
        env = WebBrowserEnv.from_mock(screenshot_path=_make_mock_screenshot(tmp_path))
        env.setup()
        result = env.step({
            "actions": [{"action_type": "done"}]
        })
        assert result.done
        env.close()

    def test_get_ops(self, tmp_path):
        env = WebBrowserEnv.from_mock(screenshot_path=_make_mock_screenshot(tmp_path))
        assert env.get_ops("gui_observer") is not None
        assert env.get_ops("gui_controller") is not None
        assert env.get_ops("web_browser") is not None
        assert env.get_ops("nonexistent") is None

    def test_health_check(self, tmp_path):
        env = WebBrowserEnv.from_mock(screenshot_path=_make_mock_screenshot(tmp_path))
        env.setup()
        health = env.health_check()
        assert health.get("ok") is True
        env.close()


# ---- Conformance: WebBrowserEnv satisfies EnvironmentAdapter ----

class TestWebBrowserEnvConformance:
    def test_observe_returns_env_observation(self, tmp_path):
        env = WebBrowserEnv.from_mock(screenshot_path=_make_mock_screenshot(tmp_path))
        env.setup()
        obs = env.observe()
        assert hasattr(obs, "data")
        assert hasattr(obs, "metadata")
        env.close()

    def test_step_returns_env_step_result(self, tmp_path):
        env = WebBrowserEnv.from_mock(screenshot_path=_make_mock_screenshot(tmp_path))
        env.setup()
        result = env.step({"actions": [{"action_type": "click", "x": 10, "y": 20}]})
        assert hasattr(result, "observation")
        assert hasattr(result, "done")
        assert hasattr(result, "info")
        env.close()

    def test_action_space_serializable(self, tmp_path):
        env = WebBrowserEnv.from_mock(screenshot_path=_make_mock_screenshot(tmp_path))
        d = env.action_space().to_dict()
        serialized = json.dumps(d, ensure_ascii=False)
        assert isinstance(serialized, str)
