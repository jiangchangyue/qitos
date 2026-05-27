"""Web-specific GUI action vocabulary extending desktop actions."""

from __future__ import annotations

from typing import Any, Dict, List

from qitos.core.multimodal import ActionSpace

from ..desktop.actions import (
    DESKTOP_ACTION_REQUIRED_ARGS,
    GUI_ACTION_NAMES,
    action_result_payload,
    normalize_gui_action,
    validate_gui_action,
)

WEB_ACTION_NAMES = (
    "navigate",
    "go_back",
    "go_forward",
    "switch_tab",
    "close_tab",
)

WEB_ACTION_REQUIRED_ARGS: Dict[str, List[str]] = {
    "navigate": ["url"],
    "go_back": [],
    "go_forward": [],
    "switch_tab": ["index"],
    "close_tab": [],
}

ALL_WEB_GUI_ACTIONS = list(GUI_ACTION_NAMES) + list(WEB_ACTION_NAMES)

ALL_WEB_REQUIRED_ARGS: Dict[str, List[str]] = {}
ALL_WEB_REQUIRED_ARGS.update(DESKTOP_ACTION_REQUIRED_ARGS)
ALL_WEB_REQUIRED_ARGS.update(WEB_ACTION_REQUIRED_ARGS)


def web_action_space() -> ActionSpace:
    """Return an action space combining desktop GUI + web browser actions."""
    return ActionSpace(
        id="web_browser_v1",
        allowed_actions=list(ALL_WEB_GUI_ACTIONS),
        required_args={k: list(v) for k, v in ALL_WEB_REQUIRED_ARGS.items()},
        metadata={
            "lane": "web",
            "extends": "desktop_gui_v1",
            "web_actions": list(WEB_ACTION_NAMES),
        },
    )


def validate_web_gui_action(payload: Any) -> Dict[str, Any]:
    """Validate an action against the web browser action space."""
    normalized = normalize_gui_action(payload)
    return web_action_space().validate(normalized)


__all__ = [
    "ALL_WEB_GUI_ACTIONS",
    "ALL_WEB_REQUIRED_ARGS",
    "WEB_ACTION_NAMES",
    "WEB_ACTION_REQUIRED_ARGS",
    "action_result_payload",
    "normalize_gui_action",
    "validate_gui_action",
    "validate_web_gui_action",
    "web_action_space",
]
