"""Model-native interaction protocol selection and rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence


ToolSchemaRenderer = Callable[[Any], str]


@dataclass(frozen=True)
class ModelProtocol:
    id: str
    display_name: str
    parser_factory: Callable[[], Any]
    prompt_renderer: Callable[[str, Any], str]
    tool_schema_renderer: ToolSchemaRenderer
    supports_multi_action: bool = False
    supports_native_tool_call_markup: bool = False
    diagnostic_style: str = "structured"
    fallback_protocols: tuple[str, ...] = field(default_factory=tuple)


def _tool_specs(tool_registry: Any) -> List[Dict[str, Any]]:
    if tool_registry is None:
        return []
    if hasattr(tool_registry, "list_tools") and hasattr(tool_registry, "describe_tool"):
        out: List[Dict[str, Any]] = []
        for name in tool_registry.list_tools():
            try:
                out.append(tool_registry.describe_tool(name))
            except Exception:
                continue
        return out
    return []


def _param_rows(spec: Dict[str, Any]) -> List[tuple[str, str]]:
    schema = spec.get("input_schema") or {}
    props = schema.get("properties") if isinstance(schema, dict) else {}
    rows: List[tuple[str, str]] = []
    if isinstance(props, dict):
        for key, value in props.items():
            if isinstance(value, dict):
                rows.append((str(key), str(value.get("type") or "any")))
            else:
                rows.append((str(key), "any"))
    return rows


def render_react_tool_schema(tool_registry: Any) -> str:
    lines: List[str] = []
    for spec in _tool_specs(tool_registry):
        lines.append(f"- {spec['name']}: {spec.get('description') or ''}".rstrip())
        params = _param_rows(spec)
        if params:
            lines.append("  Parameters:")
            for name, kind in params:
                lines.append(f"  - {name}: {kind}")
    return "\n".join(lines).strip()


def render_json_tool_schema(tool_registry: Any) -> str:
    import json

    payload: List[Dict[str, Any]] = []
    for spec in _tool_specs(tool_registry):
        payload.append(
            {
                "name": spec.get("name"),
                "description": spec.get("description"),
                "parameters": (spec.get("input_schema") or {}).get("properties", {}),
                "required": (spec.get("input_schema") or {}).get("required", []),
            }
        )
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_xml_tool_schema(tool_registry: Any) -> str:
    lines: List[str] = []
    for spec in _tool_specs(tool_registry):
        lines.append(f'<tool name="{spec["name"]}">')
        if spec.get("description"):
            lines.append(f"  <description>{spec['description']}</description>")
        params = _param_rows(spec)
        if params:
            lines.append("  <parameters>")
            for name, kind in params:
                lines.append(f'    <param name="{name}" type="{kind}" />')
            lines.append("  </parameters>")
        lines.append("</tool>")
    return "\n".join(lines).strip()


def render_minimax_tool_schema(tool_registry: Any) -> str:
    lines: List[str] = []
    for spec in _tool_specs(tool_registry):
        lines.append(f'<invoke name="{spec["name"]}">')
        if spec.get("description"):
            lines.append(f"  <description>{spec['description']}</description>")
        for name, kind in _param_rows(spec):
            lines.append(f'  <parameter name="{name}" type="{kind}">value</parameter>')
        lines.append("</invoke>")
    return "\n".join(lines).strip()


_REACT_CONTRACT = """Output contract:
- Tool call:
Thought: <brief reasoning>
Action: tool_name(arg=value, ...)

- Final answer:
Final Answer: <answer>"""

_JSON_CONTRACT = """Output contract:
- Tool call:
{"thought":"...","action":{"name":"tool_name","args":{"key":"value"}}}

- Final answer:
{"thought":"...","final_answer":"..."}"""

_XML_CONTRACT = """Output contract:
- Tool call:
<decision mode="act"><think>...</think><action name="tool_name"><arg name="key">value</arg></action></decision>

- Final answer:
<decision mode="final"><think>...</think><final_answer>...</final_answer></decision>"""

_TERMINUS_JSON_CONTRACT = """Output contract:
{
  "analysis": "...",
  "plan": "...",
  "commands": [{"keystrokes":"...", "duration":0.1}],
  "tools": [{"name":"tool_name","args":{}}],
  "task_complete": false
}"""

_TERMINUS_XML_CONTRACT = """Output contract:
<response>
  <analysis>...</analysis>
  <plan>...</plan>
  <commands><keystrokes duration="0.1">...</keystrokes></commands>
  <tools><tool name="tool_name"><arg name="key">value</arg></tool></tools>
  <task_complete>false</task_complete>
</response>"""

_MINIMAX_CONTRACT = """Output contract:
- Tool call:
<minimax:tool_call>
  <invoke name="tool_name">
    <parameter name="key">value</parameter>
  </invoke>
</minimax:tool_call>

- Completion:
<minimax:response>
  <analysis>...</analysis>
  <plan>...</plan>
  <task_complete>true</task_complete>
</minimax:response>

Rules:
- Do not emit markdown fences.
- Use one or more <invoke> blocks when calling tools.
- Use <task_complete>true</task_complete> only when the task is done."""


def _compose_prompt(
    base_prompt: str, tool_registry: Any, *, contract: str, renderer: ToolSchemaRenderer
) -> str:
    base = str(base_prompt or "").strip()
    parts: List[str] = [base] if base else []
    schema = renderer(tool_registry)
    if schema:
        parts.append(f"Available tools:\n{schema}")
    parts.append(contract.strip())
    return "\n\n".join(part for part in parts if part)


def _react_prompt(base_prompt: str, tool_registry: Any) -> str:
    return _compose_prompt(
        base_prompt,
        tool_registry,
        contract=_REACT_CONTRACT,
        renderer=render_react_tool_schema,
    )


def _json_prompt(base_prompt: str, tool_registry: Any) -> str:
    return _compose_prompt(
        base_prompt,
        tool_registry,
        contract=_JSON_CONTRACT,
        renderer=render_json_tool_schema,
    )


def _xml_prompt(base_prompt: str, tool_registry: Any) -> str:
    return _compose_prompt(
        base_prompt,
        tool_registry,
        contract=_XML_CONTRACT,
        renderer=render_xml_tool_schema,
    )


def _terminus_json_prompt(base_prompt: str, tool_registry: Any) -> str:
    return _compose_prompt(
        base_prompt,
        tool_registry,
        contract=_TERMINUS_JSON_CONTRACT,
        renderer=render_json_tool_schema,
    )


def _terminus_xml_prompt(base_prompt: str, tool_registry: Any) -> str:
    return _compose_prompt(
        base_prompt,
        tool_registry,
        contract=_TERMINUS_XML_CONTRACT,
        renderer=render_xml_tool_schema,
    )


def _minimax_prompt(base_prompt: str, tool_registry: Any) -> str:
    return _compose_prompt(
        base_prompt,
        tool_registry,
        contract=_MINIMAX_CONTRACT,
        renderer=render_minimax_tool_schema,
    )


def _protocol_table() -> Dict[str, ModelProtocol]:
    from qitos.kit.parser import (
        JsonDecisionParser,
        ReActTextParser,
        TerminusJsonParser,
        TerminusXmlParser,
        XmlDecisionParser,
    )
    from qitos.kit.parser.minimax_tool_call_parser import MiniMaxToolCallParser

    return {
        "react_text_v1": ModelProtocol(
            id="react_text_v1",
            display_name="ReAct Text",
            parser_factory=ReActTextParser,
            prompt_renderer=_react_prompt,
            tool_schema_renderer=render_react_tool_schema,
        ),
        "json_decision_v1": ModelProtocol(
            id="json_decision_v1",
            display_name="JSON Decision",
            parser_factory=JsonDecisionParser,
            prompt_renderer=_json_prompt,
            tool_schema_renderer=render_json_tool_schema,
        ),
        "xml_decision_v1": ModelProtocol(
            id="xml_decision_v1",
            display_name="XML Decision",
            parser_factory=XmlDecisionParser,
            prompt_renderer=_xml_prompt,
            tool_schema_renderer=render_xml_tool_schema,
        ),
        "terminus_json_v1": ModelProtocol(
            id="terminus_json_v1",
            display_name="Terminus JSON",
            parser_factory=TerminusJsonParser,
            prompt_renderer=_terminus_json_prompt,
            tool_schema_renderer=render_json_tool_schema,
            supports_multi_action=True,
            fallback_protocols=("terminus_xml_v1", "json_decision_v1"),
        ),
        "terminus_xml_v1": ModelProtocol(
            id="terminus_xml_v1",
            display_name="Terminus XML",
            parser_factory=TerminusXmlParser,
            prompt_renderer=_terminus_xml_prompt,
            tool_schema_renderer=render_xml_tool_schema,
            supports_multi_action=True,
            fallback_protocols=("terminus_json_v1", "xml_decision_v1"),
        ),
        "minimax_tool_call_v1": ModelProtocol(
            id="minimax_tool_call_v1",
            display_name="MiniMax Tool Call",
            parser_factory=MiniMaxToolCallParser,
            prompt_renderer=_minimax_prompt,
            tool_schema_renderer=render_minimax_tool_schema,
            supports_multi_action=True,
            supports_native_tool_call_markup=True,
            fallback_protocols=(
                "terminus_xml_v1",
                "terminus_json_v1",
                "json_decision_v1",
            ),
        ),
    }


def list_protocols() -> List[str]:
    return sorted(_protocol_table().keys())


def get_protocol(protocol: str | ModelProtocol | None) -> Optional[ModelProtocol]:
    if protocol is None:
        return None
    if isinstance(protocol, ModelProtocol):
        return protocol
    return _protocol_table().get(str(protocol).strip())


def require_protocol(protocol: str | ModelProtocol) -> ModelProtocol:
    resolved = get_protocol(protocol)
    if resolved is None:
        raise ValueError(f"Unknown model protocol: {protocol}")
    return resolved


def infer_protocol_from_parser(parser: Any) -> Optional[ModelProtocol]:
    contract = str(getattr(parser, "contract_id", "") or "").strip()
    if not contract:
        return None
    table = _protocol_table()
    if contract in table:
        return table[contract]
    for item in table.values():
        if str(getattr(item.parser_factory(), "contract_id", "")) == contract:
            return item
    return None


def resolve_protocol_chain(primary: str | ModelProtocol | None) -> List[ModelProtocol]:
    start = get_protocol(primary)
    if start is None:
        return []
    out: List[ModelProtocol] = []
    seen: set[str] = set()

    def visit(item: ModelProtocol) -> None:
        if item.id in seen:
            return
        seen.add(item.id)
        out.append(item)
        for fallback in item.fallback_protocols:
            resolved = get_protocol(fallback)
            if resolved is not None:
                visit(resolved)

    visit(start)
    return out


def render_protocol_prompt(
    base_prompt: str, protocol: str | ModelProtocol | None, tool_registry: Any
) -> str:
    resolved = get_protocol(protocol)
    if resolved is None:
        return str(base_prompt or "")
    return resolved.prompt_renderer(str(base_prompt or ""), tool_registry)


def render_protocol_tool_schema(
    tool_registry: Any, protocol: str | ModelProtocol | None
) -> str:
    resolved = get_protocol(protocol)
    if resolved is None:
        return render_react_tool_schema(tool_registry)
    return resolved.tool_schema_renderer(tool_registry)


def protocol_summary(protocol: str | ModelProtocol | None) -> Dict[str, Any]:
    resolved = get_protocol(protocol)
    if resolved is None:
        return {}
    return {
        "id": resolved.id,
        "display_name": resolved.display_name,
        "supports_multi_action": resolved.supports_multi_action,
        "supports_native_tool_call_markup": resolved.supports_native_tool_call_markup,
        "fallback_protocols": list(resolved.fallback_protocols),
    }


__all__ = [
    "ModelProtocol",
    "get_protocol",
    "require_protocol",
    "list_protocols",
    "resolve_protocol_chain",
    "render_protocol_prompt",
    "render_protocol_tool_schema",
    "render_react_tool_schema",
    "render_json_tool_schema",
    "render_xml_tool_schema",
    "render_minimax_tool_schema",
    "infer_protocol_from_parser",
    "protocol_summary",
]
