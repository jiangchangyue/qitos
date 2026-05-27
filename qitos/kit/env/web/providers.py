"""Web browser environment providers for QitOS."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from qitos.core.multimodal import guess_mime_type

from .actions import normalize_gui_action, action_result_payload


class WebBrowserProvider(ABC):
    """Abstract web browser runtime provider."""

    name: str = "web_browser_provider"
    version: str = "0.1"

    @abstractmethod
    def start(self) -> None:
        """Start or attach to the browser runtime."""

    @abstractmethod
    def reset(self, task: Any = None, start_url: Optional[str] = None) -> None:
        """Reset browser state for one task run."""

    @abstractmethod
    def stop(self) -> None:
        """Stop or release browser resources."""

    @abstractmethod
    def capture_state(self) -> Dict[str, Any]:
        """Return screenshot/DOM/a11y state."""

    @abstractmethod
    def execute_action(self, action: Any, state: Any = None) -> Dict[str, Any]:
        """Execute one normalized GUI or web action."""

    def health_check(self) -> Dict[str, Any]:
        return {"ok": True, "provider": self.name, "version": self.version}


class MockBrowserProvider(WebBrowserProvider):
    """Deterministic in-memory browser provider for smoke tests."""

    name = "mock_browser"
    version = "0.1"

    def __init__(
        self,
        *,
        screenshot_path: str,
        instruction: str = "",
        dom: Any = None,
        accessibility_tree: Any = None,
        ocr: Optional[List[Dict[str, Any]]] = None,
        ui_candidates: Optional[List[Dict[str, Any]]] = None,
        url: str = "about:blank",
        screen_size: tuple[int, int] = (1280, 720),
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.screenshot_path = str(Path(screenshot_path).expanduser().resolve())
        self.instruction = str(instruction or "")
        self.dom = dom
        self.accessibility_tree = accessibility_tree
        self.ocr = list(ocr or [])
        self.ui_candidates = list(ui_candidates or [])
        self.url = str(url or "about:blank")
        self.screen_size = tuple(screen_size)
        self.metadata = dict(metadata or {})
        self.actions: List[Dict[str, Any]] = []
        self.tab_history: List[str] = [self.url]
        self.started = False

    def start(self) -> None:
        self.started = True

    def reset(self, task: Any = None, start_url: Optional[str] = None) -> None:
        self.started = True
        self.actions = []
        if start_url:
            self.url = start_url
            self.tab_history = [start_url]

    def stop(self) -> None:
        self.started = False

    def capture_state(self) -> Dict[str, Any]:
        return {
            "screenshot": {
                "path": self.screenshot_path,
                "mime_type": guess_mime_type(self.screenshot_path),
                "detail": "original",
            },
            "dom": self.dom,
            "accessibility_tree": self.accessibility_tree,
            "ocr": list(self.ocr),
            "ui_candidates": list(self.ui_candidates),
            "instruction": self.instruction,
            "url": self.url,
            "screen_size": {"width": int(self.screen_size[0]), "height": int(self.screen_size[1])},
            "metadata": dict(self.metadata),
            "action_history": list(self.actions),
        }

    def execute_action(self, action: Any, state: Any = None) -> Dict[str, Any]:
        _ = state
        normalized = normalize_gui_action(action)
        action_type = normalized.get("action_type", "")
        self.actions.append(normalized)

        # Handle web-specific actions
        if action_type == "navigate":
            target_url = normalized.get("args", {}).get("url", "")
            self.url = target_url
            self.tab_history.append(target_url)
        elif action_type == "go_back":
            if len(self.tab_history) > 1:
                self.tab_history.pop()
                self.url = self.tab_history[-1]
        elif action_type == "go_forward":
            pass  # Mock doesn't track forward history

        return action_result_payload(
            action=normalized,
            status="success",
            execution_state="executed",
            message=f"Executed {action_type} in mock browser runtime.",
            provider=self.name,
            metadata={"url": self.url, "screen_size": list(self.screen_size)},
        )


class PlaywrightBrowserProvider(WebBrowserProvider):
    """Playwright-backed web browser provider for real browser control.

    Requires ``playwright`` to be installed (``pip install qitos[web]``).
    """

    name = "playwright_browser"
    version = "0.1"

    def __init__(
        self,
        *,
        screenshot_dir: str = ".",
        headless: bool = True,
        browser_type: str = "chromium",
        start_url: str = "about:blank",
        screen_size: tuple[int, int] = (1280, 720),
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.screenshot_dir = str(Path(screenshot_dir).expanduser().resolve())
        self.headless = headless
        self.browser_type = browser_type
        self.start_url = start_url
        self.screen_size = tuple(screen_size)
        self.metadata = dict(metadata or {})
        self._playwright = None
        self._browser = None
        self._page = None
        self._screenshot_counter = 0
        self.actions: List[Dict[str, Any]] = []
        self.started = False

    def start(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise ImportError(
                "Playwright is required for PlaywrightBrowserProvider. "
                "Install with: pip install qitos[web]"
            ) from exc

        self._playwright = sync_playwright().start()
        browser_launcher = getattr(self._playwright, self.browser_type, None)
        if browser_launcher is None:
            raise ValueError(f"Unknown browser type: {self.browser_type}")
        self._browser = browser_launcher.launch(headless=self.headless)
        self._page = self._browser.new_page(
            viewport={"width": self.screen_size[0], "height": self.screen_size[1]},
        )
        self._page.goto(self.start_url, wait_until="domcontentloaded", timeout=30000)
        self.started = True

    def reset(self, task: Any = None, start_url: Optional[str] = None) -> None:
        url = start_url or self.start_url
        if self._page is not None:
            self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
        self.actions = []
        self._screenshot_counter = 0

    def stop(self) -> None:
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()
        self._browser = None
        self._page = None
        self._playwright = None
        self.started = False

    def capture_state(self) -> Dict[str, Any]:
        if self._page is None:
            return {"error": "browser not started"}

        # Capture screenshot
        self._screenshot_counter += 1
        screenshot_filename = f"screenshot_{self._screenshot_counter:04d}.png"
        screenshot_path = str(Path(self.screenshot_dir) / screenshot_filename)
        self._page.screenshot(path=screenshot_path)

        # Capture DOM
        dom = self._page.content()

        # Capture accessibility tree
        a11y = None
        try:
            a11y = self._page.accessibility.snapshot()
        except Exception:
            pass

        # Capture URL
        url = self._page.url

        return {
            "screenshot": {
                "path": screenshot_path,
                "mime_type": "image/png",
                "detail": "original",
            },
            "dom": dom,
            "accessibility_tree": a11y,
            "ocr": [],
            "ui_candidates": [],
            "instruction": "",
            "url": url,
            "screen_size": {"width": int(self.screen_size[0]), "height": int(self.screen_size[1])},
            "metadata": dict(self.metadata),
            "action_history": list(self.actions),
        }

    def execute_action(self, action: Any, state: Any = None) -> Dict[str, Any]:
        if self._page is None:
            return action_result_payload(
                action=action, status="error", message="browser not started",
                provider=self.name, execution_state="failed",
            )

        normalized = normalize_gui_action(action)
        action_type = normalized.get("action_type", "")
        args = normalized.get("args", {})
        self.actions.append(normalized)

        try:
            if action_type == "click":
                self._page.mouse.click(float(args.get("x", 0)), float(args.get("y", 0)))
            elif action_type == "type_text":
                self._page.keyboard.type(str(args.get("text", "")))
            elif action_type == "scroll":
                self._page.mouse.wheel(float(args.get("delta_x", 0)), float(args.get("delta_y", 0)))
            elif action_type == "hotkey":
                keys = args.get("keys", [])
                if isinstance(keys, list):
                    self._page.keyboard.press("+".join(str(k) for k in keys))
                else:
                    self._page.keyboard.press(str(keys))
            elif action_type == "press_key":
                self._page.keyboard.press(str(args.get("key", "")))
            elif action_type == "navigate":
                self._page.goto(str(args.get("url", "")), wait_until="domcontentloaded", timeout=30000)
            elif action_type == "go_back":
                self._page.go_back(wait_until="domcontentloaded", timeout=30000)
            elif action_type == "go_forward":
                self._page.go_forward(wait_until="domcontentloaded", timeout=30000)
            elif action_type == "wait":
                import time
                time.sleep(float(args.get("seconds", 1)))
            elif action_type in ("done", "fail"):
                pass
            else:
                return action_result_payload(
                    action=normalized, status="error",
                    message=f"unsupported action: {action_type}",
                    provider=self.name, execution_state="failed",
                )

            return action_result_payload(
                action=normalized, status="success", execution_state="executed",
                message=f"Executed {action_type} in playwright browser.",
                provider=self.name,
                metadata={"url": self._page.url},
            )
        except Exception as exc:
            return action_result_payload(
                action=normalized, status="error", execution_state="failed",
                message=str(exc), provider=self.name,
                metadata={"url": self._page.url if self._page else ""},
            )

    def health_check(self) -> Dict[str, Any]:
        if not self.started or self._browser is None:
            return {"ok": False, "message": "browser not started", "provider": self.name}
        return {"ok": True, "provider": self.name, "version": self.version}


__all__ = [
    "MockBrowserProvider",
    "PlaywrightBrowserProvider",
    "WebBrowserProvider",
]
