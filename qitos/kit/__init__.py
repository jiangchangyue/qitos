"""Curated practical building blocks for common QiTOS agent authoring."""

from . import critic, env, evaluate, history, memory, metric, parser, planning, prompts, state, tool
from .critic import ReActSelfReflectionCritic
from .env import HostEnv, RepoEnv, TextWebEnv
from .history import WindowHistory
from .memory import MarkdownFileMemory, WindowMemory
from .parser import JsonDecisionParser, ReActTextParser, XmlDecisionParser
from .planning import DynamicTreeSearch, NumberedPlanBuilder, format_action
from .prompts import (
    JSON_DECISION_SYSTEM_PROMPT,
    PLAN_DRAFT_PROMPT,
    PLAN_EXEC_SYSTEM_PROMPT,
    REACT_SYSTEM_PROMPT,
    SWE_AGENT_SYSTEM_PROMPT,
    XML_DECISION_SYSTEM_PROMPT,
    render_prompt,
)
from .tool import (
    CodingToolSet,
    EpubToolSet,
    EditorToolSet,
    HTMLExtractText,
    HTTPGet,
    ReadFile,
    RunCommand,
    TaskToolSet,
    WriteFile,
)

__all__ = [
    "critic",
    "env",
    "evaluate",
    "history",
    "memory",
    "metric",
    "parser",
    "planning",
    "prompts",
    "state",
    "tool",
    "ReActTextParser",
    "JsonDecisionParser",
    "XmlDecisionParser",
    "REACT_SYSTEM_PROMPT",
    "PLAN_DRAFT_PROMPT",
    "PLAN_EXEC_SYSTEM_PROMPT",
    "XML_DECISION_SYSTEM_PROMPT",
    "JSON_DECISION_SYSTEM_PROMPT",
    "SWE_AGENT_SYSTEM_PROMPT",
    "render_prompt",
    "EditorToolSet",
    "CodingToolSet",
    "RunCommand",
    "HTTPGet",
    "HTMLExtractText",
    "ReadFile",
    "WriteFile",
    "EpubToolSet",
    "TaskToolSet",
    "MarkdownFileMemory",
    "WindowMemory",
    "WindowHistory",
    "NumberedPlanBuilder",
    "DynamicTreeSearch",
    "format_action",
    "ReActSelfReflectionCritic",
    "HostEnv",
    "RepoEnv",
    "TextWebEnv",
]
