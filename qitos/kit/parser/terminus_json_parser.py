"""QiTOS parser for Terminus JSON plain output."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from qitos.core.decision import Decision
from qitos.engine.parser import BaseParser, attach_parser_warning, parser_wait_decision
from qitos.kit.parser.parser_utils import (
    extract_balanced_object_candidates,
    parse_object_like_detailed,
    strip_code_fences,
)


class TerminusJsonParser(BaseParser[dict[str, Any]]):
    contract_id = "terminus_json_v1"

    def parse(
        self, raw_output: Any, context: Optional[Dict[str, Any]] = None
    ) -> Decision[dict[str, Any]]:
        text = str(raw_output or "")
        result, warnings, extraction_mode = self._extract_payload(text)
        if result is None:
            return parser_wait_decision(
                parser=self,
                code="invalid_json",
                summary="Could not parse a valid Terminus JSON payload.",
                raw_output=text,
                details=self._format_feedback("No valid JSON object found.", warnings),
                repair_instruction="Return valid JSON with analysis, plan, and either commands, tools, or task_complete=true.",
                expected_shape='{"analysis":"...","plan":"...","commands":[...],"tools":[...],"task_complete":false}',
                extraction_mode=extraction_mode,
                extra_meta={"raw_output": text, "output_format": "json"},
            )

        validation_error = self._validate_payload(result)
        if validation_error:
            return parser_wait_decision(
                parser=self,
                code=(
                    "missing_required_field"
                    if validation_error.startswith("Missing required fields")
                    else "invalid_action_schema"
                ),
                summary=validation_error,
                raw_output=text,
                details=self._format_feedback(validation_error, warnings),
                repair_instruction="Return valid JSON with analysis, plan, and either commands, tools, or task_complete=true.",
                expected_shape='{"analysis":"...","plan":"...","commands":[...],"tools":[...],"task_complete":false}',
                extraction_mode=extraction_mode,
                rationale=result.get("analysis") or validation_error,
                extra_meta={
                    "raw_output": text,
                    "analysis": str(result.get("analysis") or ""),
                    "plan": str(result.get("plan") or ""),
                    "output_format": "json",
                },
            )

        analysis = str(result.get("analysis") or "").strip()
        plan = str(result.get("plan") or "").strip()
        meta: Dict[str, Any] = {
            "analysis": analysis,
            "plan": plan,
            "output_format": "json",
        }
        if warnings:
            meta = attach_parser_warning(
                meta,
                parser=self,
                code="salvaged_json_payload",
                summary="Parser warnings were recorded while reading Terminus JSON output.",
                raw_output=text,
                details=self._format_feedback("Parser warnings.", warnings),
                expected_shape='{"analysis":"...","plan":"...","commands":[...],"tools":[...],"task_complete":false}',
                extraction_mode=extraction_mode,
                salvage_applied=True,
                salvage_summary=self._format_feedback("Parser warnings.", warnings),
            )

        commands, command_error = self._parse_commands(result.get("commands") or [])
        tools, tool_error = self._parse_tools(result.get("tools") or [])
        is_complete = self._as_bool(result.get("task_complete", False))
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
                    expected_shape='{"analysis":"...","plan":"...","commands":[...],"tools":[...],"task_complete":false}',
                    extraction_mode=extraction_mode,
                )
                return Decision.wait(rationale=analysis, meta=meta)
            return parser_wait_decision(
                parser=self,
                code="invalid_action_schema",
                summary=action_error,
                raw_output=text,
                details=self._format_feedback(action_error, warnings),
                repair_instruction="Return valid Terminus JSON with well-formed commands/tools entries, or set task_complete=true if the task is done.",
                expected_shape='{"analysis":"...","plan":"...","commands":[{"keystrokes":"...","duration":0.1}],"tools":[{"name":"tool_name","args":{}}],"task_complete":false}',
                extraction_mode=extraction_mode,
                rationale=analysis or action_error,
                extra_meta=meta,
            )

        actions = commands + tools
        if actions:
            return Decision.act(actions=actions, rationale=analysis, meta=meta)
        if is_complete:
            meta["task_complete_requested"] = True
            return Decision.wait(rationale=analysis, meta=meta)
        return parser_wait_decision(
            parser=self,
            code="missing_action_or_final",
            summary="No actions were provided.",
            raw_output=text,
            details=self._format_feedback(
                "The Terminus payload did not include commands, tools, or task_complete=true.",
                warnings,
            ),
            repair_instruction="Return at least one terminal command, one tool action, or set task_complete=true if the task is complete.",
            expected_shape='{"analysis":"...","plan":"...","commands":[...],"tools":[...],"task_complete":false}',
            extraction_mode=extraction_mode,
            rationale=analysis or "No actions were provided.",
            extra_meta=meta,
        )

    def _extract_payload(
        self, text: str
    ) -> Tuple[Optional[Dict[str, Any]], List[str], str]:
        warnings: List[str] = []
        extraction_mode = "direct"
        stripped = strip_code_fences(text)
        if stripped != text.strip():
            warnings.append(
                "AUTO-CORRECTED: stripped markdown code fences around Terminus JSON payload."
            )
            text = stripped
            extraction_mode = "fenced"

        snippet, snippet_warnings = self._extract_json_snippet(text)
        candidate_specs: List[Tuple[str, str, List[str]]] = []
        direct_candidate = text.strip()
        if direct_candidate:
            candidate_specs.append((direct_candidate, extraction_mode, []))
        balanced = sorted(
            extract_balanced_object_candidates(text), key=len, reverse=True
        )
        for candidate in balanced:
            if (
                candidate
                and candidate != direct_candidate
                and all(existing != candidate for existing, _, _ in candidate_specs)
            ):
                candidate_specs.append((candidate, "extracted", []))
        if (
            snippet
            and snippet != direct_candidate
            and all(existing != snippet for existing, _, _ in candidate_specs)
        ):
            candidate_specs.append((snippet, "extracted", list(snippet_warnings)))
        for candidate, candidate_mode, candidate_warnings in candidate_specs:
            if not candidate:
                continue
            parsed, parsed_mode = parse_object_like_detailed(
                candidate,
                json_mode=candidate_mode,
                literal_mode="python_literal",
            )
            if isinstance(parsed, dict):
                final_mode = parsed_mode or candidate_mode
                combined_warnings = warnings + list(candidate_warnings)
                if candidate_mode == "extracted":
                    combined_warnings.append(
                        "AUTO-CORRECTED: extracted a JSON-like object from surrounding text."
                    )
                if final_mode == "python_literal":
                    combined_warnings.append(
                        "AUTO-CORRECTED: parsed JSON-like payload using Python literal rules."
                    )
                return parsed, combined_warnings, final_mode
            fixed = self._try_fix_json(candidate)
            if fixed is not None:
                try:
                    parsed = json.loads(fixed)
                    if isinstance(parsed, dict):
                        combined_warnings = warnings + list(candidate_warnings)
                        combined_warnings.append(
                            "AUTO-CORRECTED: inserted missing closing braces in JSON payload."
                        )
                        if candidate_mode == "extracted":
                            combined_warnings.append(
                                "AUTO-CORRECTED: extracted a JSON-like object from surrounding text."
                            )
                        return parsed, combined_warnings, "brace_fix"
                except json.JSONDecodeError:
                    pass
        if not candidate_specs:
            return (
                None,
                warnings + snippet_warnings,
                extraction_mode if warnings else "",
            )
        try:
            json.loads(candidate_specs[0][0])
        except json.JSONDecodeError as exc:
            return (
                None,
                warnings + candidate_specs[0][2] + [f"Invalid JSON: {exc}"],
                candidate_specs[0][1],
            )
        return (
            None,
            warnings + candidate_specs[0][2] + ["Response must be a JSON object."],
            candidate_specs[0][1],
        )

    def _extract_json_snippet(self, text: str) -> Tuple[str, List[str]]:
        warnings: List[str] = []
        start = -1
        depth = 0
        in_string = False
        escape = False
        for idx, char in enumerate(text):
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == "{":
                if depth == 0:
                    start = idx
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0 and start != -1:
                    end = idx + 1
                    before = text[:start].strip()
                    after = text[end:].strip()
                    if before:
                        warnings.append("Extra text detected before the JSON object.")
                    if after:
                        warnings.append("Extra text detected after the JSON object.")
                    return text[start:end], warnings
        if start != -1:
            before = text[:start].strip()
            if before:
                warnings.append("Extra text detected before the JSON object.")
            return text[start:].strip(), warnings
        return "", ["No JSON object found in model output."]

    def _try_fix_json(self, text: str) -> Optional[str]:
        stripped = text.strip()
        if not stripped.startswith("{"):
            return None
        depth = 0
        in_string = False
        escape = False
        for char in stripped:
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
        if depth > 0:
            return stripped + ("}" * depth)
        return None

    def _validate_payload(self, payload: Dict[str, Any]) -> Optional[str]:
        missing = [field for field in ("analysis", "plan") if field not in payload]
        if missing:
            return f"Missing required fields: {', '.join(missing)}"
        if not isinstance(payload.get("analysis"), str):
            return "Field 'analysis' must be a string."
        if not isinstance(payload.get("plan"), str):
            return "Field 'plan' must be a string."
        if "commands" in payload and not isinstance(payload.get("commands"), list):
            return "Field 'commands' must be an array."
        if "tools" in payload and not isinstance(payload.get("tools"), list):
            return "Field 'tools' must be an array."
        if (
            "commands" not in payload
            and "tools" not in payload
            and not self._as_bool(payload.get("task_complete", False))
        ):
            return "At least one of 'commands', 'tools', or 'task_complete=true' is required."
        return None

    def _parse_commands(
        self, commands_data: List[Any]
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        actions: List[Dict[str, Any]] = []
        for index, item in enumerate(commands_data, start=1):
            if not isinstance(item, dict):
                return [], f"Command {index} must be an object."
            keystrokes = item.get("keystrokes")
            if not isinstance(keystrokes, str):
                return [], f"Command {index} requires a string 'keystrokes' field."
            duration = item.get("duration", 1.0)
            if not isinstance(duration, (int, float)):
                return [], f"Command {index} has invalid duration value."
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
        return actions, None

    def _parse_tools(
        self, tools_data: List[Any]
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        actions: List[Dict[str, Any]] = []
        for index, item in enumerate(tools_data, start=1):
            if not isinstance(item, dict):
                return [], f"Tool action {index} must be an object."
            name = item.get("name")
            if not isinstance(name, str) or not name.strip():
                return (
                    [],
                    f"Tool action {index} requires a non-empty string 'name' field.",
                )
            args = item.get("args", {})
            if args is None:
                args = {}
            if not isinstance(args, dict):
                return [], f"Tool action {index} must provide an object 'args' field."
            actions.append(
                {
                    "name": name.strip(),
                    "args": args,
                    "metadata": {"tool_index": index},
                }
            )
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


__all__ = ["TerminusJsonParser"]
