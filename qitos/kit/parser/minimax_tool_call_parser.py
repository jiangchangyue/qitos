"""Parser for MiniMax-style native tool-call markup."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from qitos.core.decision import Decision
from qitos.engine.parser import BaseParser, attach_parser_warning, parser_wait_decision


class MiniMaxToolCallParser(BaseParser[dict[str, Any]]):
    contract_id = "minimax_tool_call_v1"

    def parse(self, raw_output: Any, context: Optional[Dict[str, Any]] = None) -> Decision[dict[str, Any]]:
        text = str(raw_output or "")
        payload, warnings = self._extract_payload(text)
        if not payload:
            return parser_wait_decision(
                parser=self,
                code="invalid_xml",
                summary="No valid MiniMax tool-call payload was found.",
                raw_output=text,
                details=self._format_feedback("No <invoke> or <minimax:response> block found.", warnings),
                repair_instruction="Return MiniMax tool-call markup with <invoke name=\"tool_name\"> or a completion response block.",
                expected_shape='<minimax:tool_call><invoke name="tool_name"><parameter name="key">value</parameter></invoke></minimax:tool_call>',
            )

        meta: Dict[str, Any] = {
            "analysis": self._extract_section(payload, "analysis") or "",
            "plan": self._extract_section(payload, "plan") or "",
            "output_format": "minimax_tool_call",
        }
        if warnings:
            meta = attach_parser_warning(
                meta,
                parser=self,
                code="salvaged_minimax_payload",
                summary="Parser warnings were recorded while reading MiniMax tool-call output.",
                raw_output=text,
                details=self._format_feedback("Parser warnings.", warnings),
                expected_shape='<minimax:tool_call><invoke name="tool_name"><parameter name="key">value</parameter></invoke></minimax:tool_call>',
                salvage_applied=True,
                salvage_summary=self._format_feedback("Parser warnings.", warnings),
            )

        actions, action_error = self._parse_invocations(payload)
        if action_error:
            return parser_wait_decision(
                parser=self,
                code="invalid_action_schema",
                summary=action_error,
                raw_output=text,
                details=self._format_feedback(action_error, warnings),
                repair_instruction="Return one or more <invoke name=\"tool_name\"> blocks with named <parameter> children.",
                expected_shape='<minimax:tool_call><invoke name="tool_name"><parameter name="key">value</parameter></invoke></minimax:tool_call>',
                rationale=meta.get("analysis") or action_error,
                extra_meta=meta,
            )
        if actions:
            return Decision.act(actions=actions, rationale=str(meta.get("analysis") or ""), meta=meta)

        is_complete = self._as_bool(self._extract_section(payload, "task_complete") or False)
        final_answer = self._extract_section(payload, "final_answer")
        if final_answer:
            return Decision.final(answer=final_answer, rationale=str(meta.get("analysis") or ""), meta=meta)
        if is_complete:
            meta["task_complete_requested"] = True
            return Decision.wait(rationale=str(meta.get("analysis") or "Task complete."), meta=meta)

        return parser_wait_decision(
            parser=self,
            code="missing_action_or_final",
            summary="MiniMax output did not contain an invocation or completion signal.",
            raw_output=text,
            details=self._format_feedback("No parseable <invoke>, <final_answer>, or <task_complete>true</task_complete> found.", warnings),
            repair_instruction="Return either one or more <invoke> blocks, a <final_answer>, or <task_complete>true</task_complete>.",
            expected_shape='<minimax:tool_call><invoke name="tool_name"><parameter name="key">value</parameter></invoke></minimax:tool_call>',
            rationale=str(meta.get("analysis") or ""),
            extra_meta=meta,
        )

    def _extract_payload(self, text: str) -> Tuple[str, List[str]]:
        warnings: List[str] = []
        invoke_match = re.search(r"(<(?:minimax:tool_call|tool_call)[^>]*>.*?</(?:minimax:tool_call|tool_call)>)", text, re.DOTALL)
        if invoke_match:
            before = text[: invoke_match.start()].strip()
            after = text[invoke_match.end() :].strip()
            if before:
                warnings.append("Extra text detected before MiniMax tool-call block.")
            if after:
                warnings.append("Extra text detected after MiniMax tool-call block.")
            return invoke_match.group(1), warnings
        response_match = re.search(r"(<(?:minimax:response|response)[^>]*>.*?</(?:minimax:response|response)>)", text, re.DOTALL)
        if response_match:
            before = text[: response_match.start()].strip()
            after = text[response_match.end() :].strip()
            if before:
                warnings.append("Extra text detected before MiniMax response block.")
            if after:
                warnings.append("Extra text detected after MiniMax response block.")
            return response_match.group(1), warnings
        if "<invoke" in text:
            warnings.append("AUTO-CORRECTED: extracted bare <invoke> block without explicit MiniMax wrapper.")
            return text, warnings
        return "", warnings

    def _parse_invocations(self, payload: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        matches = re.findall(r"<invoke([^>]*)>(.*?)</invoke>", payload, re.DOTALL)
        actions: List[Dict[str, Any]] = []
        for index, (attrs, body) in enumerate(matches, start=1):
            name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', attrs)
            if name_match is None:
                return [], f"Invocation {index} is missing the required name attribute."
            args: Dict[str, Any] = {}
            for param_attrs, value in re.findall(r"<parameter([^>]*)>(.*?)</parameter>", body, re.DOTALL):
                key_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', param_attrs)
                if key_match is None:
                    return [], f"Invocation {index} contains a <parameter> without a name attribute."
                args[key_match.group(1)] = value.strip()
            actions.append(
                {
                    "name": name_match.group(1).strip(),
                    "args": args,
                    "metadata": {"tool_index": index},
                }
            )
        if "<invoke" in payload and not actions:
            return [], "Unable to parse <invoke> blocks from MiniMax payload."
        return actions, None

    def _extract_section(self, payload: str, tag: str) -> Optional[str]:
        match = re.search(rf"<{tag}>(.*?)</{tag}>", payload, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

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


__all__ = ["MiniMaxToolCallParser"]
