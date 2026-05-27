"""Web browser environment for QitOS — Playwright-backed visual web agent."""

from __future__ import annotations

from typing import Any, Dict, Optional

from qitos.core import Env, EnvObservation, EnvStepResult
from qitos.core.multimodal import EnvironmentAdapter, normalize_observation_pack

from .actions import normalize_gui_action, validate_web_gui_action, web_action_space
from .controller import WebBrowserControllerOps, WebBrowserObserverOps
from .providers import MockBrowserProvider, PlaywrightBrowserProvider, WebBrowserProvider


class WebBrowserEnv(Env, EnvironmentAdapter):
    """Web browser environment with screenshot, DOM, a11y, and browser control support."""

    name = "web_browser_env"
    version = "0.6"

    def __init__(self, provider: WebBrowserProvider):
        self.provider = provider
        self.observer = WebBrowserObserverOps(provider)
        self.controller = WebBrowserControllerOps(provider)
        self._action_space = web_action_space()
        self._last_observation: Optional[EnvObservation] = None

    @classmethod
    def from_mock(
        cls,
        *,
        screenshot_path: str,
        instruction: str = "",
        dom: Any = None,
        accessibility_tree: Any = None,
        ocr: Optional[list[dict[str, Any]]] = None,
        ui_candidates: Optional[list[dict[str, Any]]] = None,
        url: str = "about:blank",
        screen_size: tuple[int, int] = (1280, 720),
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "WebBrowserEnv":
        return cls(
            MockBrowserProvider(
                screenshot_path=screenshot_path,
                instruction=instruction,
                dom=dom,
                accessibility_tree=accessibility_tree,
                ocr=ocr,
                ui_candidates=ui_candidates,
                url=url,
                screen_size=screen_size,
                metadata=metadata,
            )
        )

    @classmethod
    def from_playwright(
        cls,
        *,
        screenshot_dir: str = ".",
        headless: bool = True,
        browser_type: str = "chromium",
        start_url: str = "about:blank",
        screen_size: tuple[int, int] = (1280, 720),
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "WebBrowserEnv":
        return cls(
            PlaywrightBrowserProvider(
                screenshot_dir=screenshot_dir,
                headless=headless,
                browser_type=browser_type,
                start_url=start_url,
                screen_size=screen_size,
                metadata=metadata,
            )
        )

    def setup(self, task: Any = None, workspace: Optional[str] = None, **kwargs: Any) -> None:
        self.provider.start()

    def reset(self, task: Any = None, workspace: Optional[str] = None, **kwargs: Any) -> EnvObservation:
        start_url = kwargs.get("start_url") or kwargs.get("url")
        self.provider.reset(task=task, start_url=start_url)
        return self.observe()

    def observe(self, state: Any = None) -> EnvObservation:
        payload = self.observer.capture_observation(state=state)
        pack = normalize_observation_pack(payload)
        metadata = {
            "modalities": ["web", "screenshot"],
            "provider": getattr(self.provider, "name", self.provider.__class__.__name__),
        }
        if pack is not None and isinstance(pack.metadata, dict):
            screen_size = pack.metadata.get("screen_size")
            if screen_size is not None:
                metadata["screen_size"] = screen_size
            url = pack.metadata.get("url")
            if url is not None:
                metadata["url"] = url
        observation = EnvObservation(
            data={
                "multimodal": payload,
                "web": {
                    "instruction": (pack.metadata.get("instruction") if pack and isinstance(pack.metadata, dict) else None),
                    "url": (pack.metadata.get("url") if pack and isinstance(pack.metadata, dict) else None),
                    "screen_size": (pack.metadata.get("screen_size") if pack and isinstance(pack.metadata, dict) else None),
                    "provider": getattr(self.provider, "name", self.provider.__class__.__name__),
                },
            },
            metadata=metadata,
        )
        self._last_observation = observation
        return observation

    def capabilities(self) -> Dict[str, Any]:
        screen_size = None
        url = None
        if self._last_observation is not None and isinstance(self._last_observation.data, dict):
            web_data = self._last_observation.data.get("web") or {}
            screen_size = web_data.get("screen_size")
            url = web_data.get("url")
        return {
            "gui_observer": True,
            "gui_controller": True,
            "web_browser": True,
            "provider": getattr(self.provider, "name", self.provider.__class__.__name__),
            "screen_size": screen_size,
            "url": url,
        }

    def action_space(self):
        return self._action_space

    def step(self, action: Any, state: Any = None) -> EnvStepResult:
        performed: list[dict[str, Any]] = []
        validation_errors: list[dict[str, Any]] = []
        if isinstance(action, dict):
            raw_actions = action.get("actions")
            if isinstance(raw_actions, list):
                for item in raw_actions:
                    if isinstance(item, dict):
                        normalized = normalize_gui_action(item)
                        if normalized.get("action_type"):
                            validation = validate_web_gui_action(normalized)
                            if not bool(validation.get("ok", False)):
                                validation_errors.append(
                                    {
                                        "action": normalized,
                                        "errors": list(validation.get("errors") or []),
                                    }
                                )
                                performed.append(
                                    {
                                        "status": "validation_error",
                                        "execution_state": "failed",
                                        "provider": getattr(
                                            self.provider,
                                            "name",
                                            self.provider.__class__.__name__,
                                        ),
                                        "action": normalized,
                                        "message": "; ".join(
                                            str(x) for x in (validation.get("errors") or [])
                                        ),
                                    }
                                )
                                continue
                            performed.append(self.controller.perform(normalized, state=state))
        observation = self.observe(state=state)
        done = False
        if isinstance(action, dict):
            if str(action.get("decision_mode") or "") == "final":
                done = True
            elif any(
                str((result.get("action") or {}).get("action_type") or "") in {"done", "fail"}
                for result in performed
                if isinstance(result, dict)
            ):
                done = True
        return EnvStepResult(
            observation=observation,
            done=done,
            info={
                "performed_actions": performed,
                "validation_errors": validation_errors,
                "capabilities": self.capabilities(),
                "action_space": self.action_space().to_dict(),
            },
        )

    def get_ops(self, group: str) -> Any:
        name = str(group or "").strip().lower()
        if name == "gui_observer":
            return self.observer
        if name == "gui_controller":
            return self.controller
        if name == "web_browser":
            return self.controller
        return None

    def health_check(self) -> Dict[str, Any]:
        return dict(self.provider.health_check() or {})

    def close(self) -> None:
        self.provider.stop()


__all__ = ["WebBrowserEnv"]
