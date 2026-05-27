"""Web browser observer/controller capability adapters."""

from __future__ import annotations

from typing import Any, Dict

from qitos.core import GUIControllerCapability, GUIObserverCapability
from qitos.core.multimodal import ObservationPack

from .actions import normalize_gui_action
from .providers import WebBrowserProvider


class WebBrowserObserverOps(GUIObserverCapability):
    def __init__(self, provider: WebBrowserProvider) -> None:
        self.provider = provider

    def capture_observation(self, state: Any = None) -> Dict[str, Any]:
        _ = state
        snapshot = self.provider.capture_state()
        pack = ObservationPack(
            text=str(snapshot.get("instruction") or ""),
            screenshot=dict(snapshot.get("screenshot") or {}),
            dom=snapshot.get("dom"),
            accessibility_tree=snapshot.get("accessibility_tree"),
            ui_candidates=list(snapshot.get("ui_candidates") or []),
            ocr=list(snapshot.get("ocr") or []),
            metadata={
                "url": snapshot.get("url"),
                "instruction": snapshot.get("instruction"),
                "screen_size": snapshot.get("screen_size"),
                "provider": getattr(self.provider, "name", self.provider.__class__.__name__),
                **dict(snapshot.get("metadata") or {}),
            },
        )
        return pack.to_dict()


class WebBrowserControllerOps(GUIControllerCapability):
    def __init__(self, provider: WebBrowserProvider) -> None:
        self.provider = provider

    def perform(self, action: Dict[str, Any], state: Any = None) -> Dict[str, Any]:
        normalized = normalize_gui_action(action)
        return self.provider.execute_action(normalized, state=state)


__all__ = ["WebBrowserControllerOps", "WebBrowserObserverOps"]
