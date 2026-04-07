"""QiTOS parser for Terminus XML plain output."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from qitos.core.decision import Decision
from qitos.engine.parser import BaseParser, attach_parser_warning, parser_wait_decision


class TerminusXmlParser(BaseParser[dict[str, Any]]):
    contract_id = "terminus_xml_v1"

    def parse(
        self, raw_output: Any, context: Optional[Dict[str, Any]] = None
    ) -> Decision[dict[str, Any]]:
        text = str(raw_output or "")
        payload, warnings = self._extract_response(text)
        if not payload:
            return parser_wait_decision(
                parser=self,
                code="invalid_xml",
                summary="No valid <response> block was found.",
                raw_output=text,
                details=self._format_feedback("No <response> block found.", warnings),
                repair_instruction="Return XML with a <response> root containing analysis, plan, and either commands, tools, or task_complete=true.",
                expected_shape="<response><analysis>...</analysis><plan>...</plan><commands>...</commands><tools>...</tools><task_complete>false</task_complete></response>",
                extra_meta={"raw_output": text, "output_format": "xml"},
            )

        analysis = self._extract_section(payload, "analysis")
        plan = self._extract_section(payload, "plan")
        commands_block = self._extract_section(payload, "commands")
        tools_block = self._extract_section(payload, "tools")
        task_complete = self._extract_section(payload, "task_complete")
        meta: Dict[str, Any] = {
            "analysis": analysis,
            "plan": plan,
            "output_format": "xml",
        }
        if warnings:
            meta = attach_parser_warning(
                meta,
                parser=self,
                code="salvaged_xml_payload",
                summary="Parser warnings were recorded while reading Terminus XML output.",
                raw_output=text,
                details=self._format_feedback("Parser warnings.", warnings),
                expected_shape="<response><analysis>...</analysis><plan>...</plan><commands>...</commands><tools>...</tools><task_complete>false</task_complete></response>",
                salvage_applied=True,
                salvage_summary=self._format_feedback("Parser warnings.", warnings),
            )

        missing = []
        if analysis is None:
            missing.append("analysis")
        if plan is None:
            missing.append("plan")
        if (
            commands_block is None
            and tools_block is None
            and not self._as_bool(task_complete or False)
        ):
            missing.append("commands/tools")
        if missing:
            return parser_wait_decision(
                parser=self,
                code="missing_required_field",
                summary=f"Missing required XML sections: {', '.join(missing)}",
                raw_output=text,
                details=self._format_feedback(
                    f"Missing required XML sections: {', '.join(missing)}",
                    warnings,
                ),
                repair_instruction="Return XML with <analysis>, <plan>, and either <commands>, <tools>, or <task_complete>true</task_complete>.",
                expected_shape="<response><analysis>...</analysis><plan>...</plan><commands>...</commands><tools>...</tools><task_complete>false</task_complete></response>",
                rationale=analysis
                or f"Missing required XML sections: {', '.join(missing)}",
                extra_meta=meta,
            )

        is_complete = self._as_bool(task_complete or False)
        command_actions, command_error = self._parse_commands(commands_block or "")
        tool_actions, tool_error = self._parse_tools(tools_block or "")
        action_error = command_error or tool_error
        if action_error:
            if is_complete:
                meta["task_complete_requested"] = True
                meta = attach_parser_warning(
                    meta,
                    parser=self,
                    code="invalid_action_schema",
                    summary=action_error,
                    raw_output=text,
                    details=self._format_feedback(action_error, warnings),
                    expected_shape="<response><analysis>...</analysis><plan>...</plan><commands>...</commands><tools>...</tools><task_complete>false</task_complete></response>",
                )
                return Decision.wait(
                    rationale=analysis or "Task appears complete.", meta=meta
                )
            return parser_wait_decision(
                parser=self,
                code="invalid_action_schema",
                summary=action_error,
                raw_output=text,
                details=self._format_feedback(action_error, warnings),
                repair_instruction="Return well-formed Terminus XML with valid <commands> or <tools> entries, or set task_complete=true if the task is done.",
                expected_shape='<response><analysis>...</analysis><plan>...</plan><commands><keystrokes duration="0.1">...</keystrokes></commands><tools><tool name="tool_name"></tool></tools><task_complete>false</task_complete></response>',
                rationale=analysis or action_error,
                extra_meta=meta,
            )

        actions = command_actions + tool_actions
        if actions:
            return Decision.act(actions=actions, rationale=analysis or "", meta=meta)
        if is_complete:
            meta["task_complete_requested"] = True
            return Decision.wait(
                rationale=analysis or "Task appears complete.", meta=meta
            )
        return parser_wait_decision(
            parser=self,
            code="missing_action_or_final",
            summary="No actions were provided.",
            raw_output=text,
            details=self._format_feedback(
                "The Terminus XML payload did not include commands, tools, or task_complete=true.",
                warnings,
            ),
            repair_instruction="Return at least one terminal command, one tool action, or set task_complete=true if the task is complete.",
            expected_shape="<response><analysis>...</analysis><plan>...</plan><commands>...</commands><tools>...</tools><task_complete>false</task_complete></response>",
            rationale=analysis or "No actions were provided.",
            extra_meta=meta,
        )

    def _extract_response(self, text: str) -> Tuple[str, List[str]]:
        warnings: List[str] = []
        start = text.find("<response>")
        if start == -1:
            return "", ["No <response> tag found in model output."]
        end = text.find("</response>", start)
        if end == -1:
            warnings.append("AUTO-CORRECTED: inserted missing </response> closing tag.")
            snippet = text[start:] + "\n</response>"
            before = text[:start].strip()
            if before:
                warnings.append("Extra text detected before <response>.")
            return snippet, warnings
        snippet = text[start : end + len("</response>")]
        before = text[:start].strip()
        after = text[end + len("</response>") :].strip()
        if before:
            warnings.append("Extra text detected before <response>.")
        if after:
            warnings.append("Extra text detected after </response>.")
        return snippet, warnings

    def _extract_section(self, payload: str, tag: str) -> Optional[str]:
        full = re.search(rf"<{tag}>(.*?)</{tag}>", payload, re.DOTALL)
        if full:
            return full.group(1).strip()
        if re.search(rf"<{tag}\s*/>", payload):
            return ""
        if re.search(rf"<{tag}></{tag}>", payload):
            return ""
        return None

    def _parse_commands(self, block: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        if not block.strip():
            return [], None
        matches = re.findall(r"<keystrokes([^>]*)>(.*?)</keystrokes>", block, re.DOTALL)
        actions: List[Dict[str, Any]] = []
        for index, (attrs, keystrokes) in enumerate(matches, start=1):
            duration_match = re.search(r'duration\s*=\s*["\']([^"\']*)["\']', attrs)
            duration = 1.0
            if duration_match is not None:
                try:
                    duration = float(duration_match.group(1))
                except ValueError:
                    return (
                        [],
                        f"Command {index} has invalid duration value '{duration_match.group(1)}'.",
                    )
            actions.append(
                {
                    "name": "send_terminal_keys",
                    "args": {
                        "keystrokes": keystrokes,
                        "duration_sec": float(duration),
                    },
                    "metadata": {"command_index": index},
                }
            )
        if "<keystrokes" in block and not actions:
            return [], "Unable to parse <keystrokes> elements from <commands>."
        return actions, None

    def _parse_tools(self, block: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        if not block.strip():
            return [], None
        matches = re.findall(r"<tool([^>]*)>(.*?)</tool>", block, re.DOTALL)
        actions: List[Dict[str, Any]] = []
        for index, (attrs, body) in enumerate(matches, start=1):
            name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', attrs)
            if name_match is None:
                return (
                    [],
                    f"Tool action {index} is missing the required name attribute.",
                )
            args: Dict[str, Any] = {}
            for arg_attrs, value in re.findall(
                r"<arg([^>]*)>(.*?)</arg>", body, re.DOTALL
            ):
                key_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', arg_attrs)
                if key_match is None:
                    return (
                        [],
                        f"Tool action {index} contains an <arg> without a name attribute.",
                    )
                args[key_match.group(1)] = value.strip()
            actions.append(
                {
                    "name": name_match.group(1).strip(),
                    "args": args,
                    "metadata": {"tool_index": index},
                }
            )
        if "<tool" in block and not actions:
            return [], "Unable to parse <tool> elements from <tools>."
        return actions, None

    def _as_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes"}
        return bool(value)

    def _format_feedback(self, primary: str, warnings: List[str]) -> str:
        lines = [str(primary).strip()] if str(primary).strip() else []
        lines.extend(str(item).strip() for item in warnings if str(item).strip())
        return "\n".join(lines)


__all__ = ["TerminusXmlParser"]
