"""QiTOS parser for Terminus JSON plain output."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from qitos.core.decision import Decision
from qitos.engine.parser import BaseParser


class TerminusJsonParser(BaseParser[dict[str, Any]]):
    def parse(self, raw_output: Any, context: Optional[Dict[str, Any]] = None) -> Decision[dict[str, Any]]:
        text = str(raw_output or "")
        result, warnings = self._extract_payload(text)
        if result is None:
            return Decision.wait(
                rationale="Repair the response format and try again.",
                meta={
                    "parser_error": True,
                    "parser_feedback": self._format_feedback("No valid JSON object found.", warnings),
                    "raw_output": text,
                    "output_format": "json",
                },
            )

        validation_error = self._validate_payload(result)
        if validation_error:
            return Decision.wait(
                rationale=result.get("analysis") or "Repair the response format and try again.",
                meta={
                    "parser_error": True,
                    "parser_feedback": self._format_feedback(validation_error, warnings),
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
            meta["parser_warning"] = self._format_feedback("Parser warnings.", warnings)

        commands, command_error = self._parse_commands(result.get("commands") or [])
        is_complete = self._as_bool(result.get("task_complete", False))
        if command_error:
            if is_complete:
                meta["task_complete_requested"] = True
                meta["parser_warning"] = self._format_feedback(command_error, warnings)
                return Decision.wait(rationale=analysis, meta=meta)
            meta["parser_error"] = True
            meta["parser_feedback"] = self._format_feedback(command_error, warnings)
            return Decision.wait(rationale=analysis or "Repair the response format and try again.", meta=meta)

        if commands:
            return Decision.act(actions=commands, rationale=analysis, meta=meta)
        if is_complete:
            meta["task_complete_requested"] = True
            return Decision.wait(rationale=analysis, meta=meta)
        meta["parser_feedback"] = self._format_feedback(
            "No terminal commands were provided. If you want to wait, send an empty keystroke command with a duration.",
            warnings,
        )
        meta["parser_error"] = True
        return Decision.wait(rationale=analysis or "Repair the response format and try again.", meta=meta)

    def _extract_payload(self, text: str) -> Tuple[Optional[Dict[str, Any]], List[str]]:
        warnings: List[str] = []
        snippet, snippet_warnings = self._extract_json_snippet(text)
        warnings.extend(snippet_warnings)
        if not snippet:
            return None, warnings
        try:
            parsed = json.loads(snippet)
            if isinstance(parsed, dict):
                return parsed, warnings
            return None, warnings + ["Response must be a JSON object."]
        except json.JSONDecodeError as exc:
            fixed = self._try_fix_json(snippet)
            if fixed is not None:
                try:
                    parsed = json.loads(fixed)
                    if isinstance(parsed, dict):
                        warnings.append("AUTO-CORRECTED: inserted missing closing braces in JSON payload.")
                        return parsed, warnings
                except json.JSONDecodeError:
                    pass
            return None, warnings + [f"Invalid JSON: {exc}"]

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
        missing = [field for field in ("analysis", "plan", "commands") if field not in payload]
        if missing:
            return f"Missing required fields: {', '.join(missing)}"
        if not isinstance(payload.get("analysis"), str):
            return "Field 'analysis' must be a string."
        if not isinstance(payload.get("plan"), str):
            return "Field 'plan' must be a string."
        if not isinstance(payload.get("commands"), list):
            return "Field 'commands' must be an array."
        return None

    def _parse_commands(self, commands_data: List[Any]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
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
