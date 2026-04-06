"""QiTOS parser for Terminus XML plain output."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from qitos.core.decision import Decision
from qitos.engine.parser import BaseParser


class TerminusXmlParser(BaseParser[dict[str, Any]]):
    def parse(self, raw_output: Any, context: Optional[Dict[str, Any]] = None) -> Decision[dict[str, Any]]:
        text = str(raw_output or "")
        payload, warnings = self._extract_response(text)
        if not payload:
            return Decision.wait(
                rationale="Repair the response format and try again.",
                meta={
                    "parser_error": True,
                    "parser_feedback": self._format_feedback("No <response> block found.", warnings),
                    "raw_output": text,
                    "output_format": "xml",
                },
            )

        analysis = self._extract_section(payload, "analysis")
        plan = self._extract_section(payload, "plan")
        commands_block = self._extract_section(payload, "commands")
        task_complete = self._extract_section(payload, "task_complete")
        meta: Dict[str, Any] = {
            "analysis": analysis,
            "plan": plan,
            "output_format": "xml",
        }
        if warnings:
            meta["parser_warning"] = self._format_feedback("Parser warnings.", warnings)

        missing = []
        if analysis is None:
            missing.append("analysis")
        if plan is None:
            missing.append("plan")
        if commands_block is None and not self._as_bool(task_complete or False):
            missing.append("commands")
        if missing:
            meta["parser_error"] = True
            meta["parser_feedback"] = self._format_feedback(
                f"Missing required XML sections: {', '.join(missing)}",
                warnings,
            )
            return Decision.wait(rationale=analysis or "Repair the response format and try again.", meta=meta)

        is_complete = self._as_bool(task_complete or False)
        actions, command_error = self._parse_commands(commands_block or "")
        if command_error:
            if is_complete:
                meta["task_complete_requested"] = True
                meta["parser_warning"] = self._format_feedback(command_error, warnings)
                return Decision.wait(rationale=analysis or "Task appears complete.", meta=meta)
            meta["parser_error"] = True
            meta["parser_feedback"] = self._format_feedback(command_error, warnings)
            return Decision.wait(rationale=analysis or "Repair the response format and try again.", meta=meta)

        if actions:
            return Decision.act(actions=actions, rationale=analysis or "", meta=meta)
        if is_complete:
            meta["task_complete_requested"] = True
            return Decision.wait(rationale=analysis or "Task appears complete.", meta=meta)
        meta["parser_error"] = True
        meta["parser_feedback"] = self._format_feedback(
            "No terminal commands were provided. If you want to wait, emit an empty keystrokes element with a duration.",
            warnings,
        )
        return Decision.wait(rationale=analysis or "Repair the response format and try again.", meta=meta)

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
        matches = re.findall(r'<keystrokes([^>]*)>(.*?)</keystrokes>', block, re.DOTALL)
        actions: List[Dict[str, Any]] = []
        for index, (attrs, keystrokes) in enumerate(matches, start=1):
            duration_match = re.search(r'duration\s*=\s*["\']([^"\']*)["\']', attrs)
            duration = 1.0
            if duration_match is not None:
                try:
                    duration = float(duration_match.group(1))
                except ValueError:
                    return [], f"Command {index} has invalid duration value '{duration_match.group(1)}'."
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
