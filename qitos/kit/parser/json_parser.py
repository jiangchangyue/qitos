"""JSON decision parser with configurable key mapping."""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from qitos.core.decision import Decision
from qitos.engine.parser import BaseParser, attach_parser_warning, parser_wait_decision
from qitos.kit.parser.parser_utils import (
    extract_json_actions,
    first_dict_value,
    json_payload_details,
    norm,
)


class JsonDecisionParser(BaseParser[dict[str, Any]]):
    contract_id = "json_decision_v1"

    def __init__(
        self,
        *,
        thought_keys: Optional[Sequence[str]] = None,
        reflection_keys: Optional[Sequence[str]] = None,
        action_keys: Optional[Sequence[str]] = None,
        final_keys: Optional[Sequence[str]] = None,
    ):
        self.thought_keys = tuple(
            norm(x)
            for x in (thought_keys or ("thought", "thinking", "think", "rationale"))
        )
        self.reflection_keys = tuple(
            norm(x)
            for x in (reflection_keys or ("reflection", "reflect", "selfreflection"))
        )
        self.action_keys = tuple(
            norm(x) for x in (action_keys or ("action", "tool", "call"))
        )
        self.final_keys = tuple(
            norm(x) for x in (final_keys or ("finalanswer", "final", "answer"))
        )

    def parse(
        self, raw_output: Any, context: Optional[Dict[str, Any]] = None
    ) -> Decision[dict[str, Any]]:
        try:
            payload, warnings, extraction_mode = json_payload_details(raw_output)
        except Exception as exc:
            return parser_wait_decision(
                parser=self,
                code="invalid_json",
                summary="Could not parse a valid JSON decision object.",
                raw_output=raw_output,
                details=str(exc),
                repair_instruction="Return valid JSON only, with either an action, actions, final_answer, or mode='wait'.",
                expected_shape='{"thought":"...","action":{"name":"tool_name","args":{...}}} or {"thought":"...","final_answer":"..."}',
            )
        thought = first_dict_value(payload, self.thought_keys)
        reflection = first_dict_value(payload, self.reflection_keys)
        mode = norm(str(payload.get("mode", "")))
        meta = {"reflection": reflection} if reflection else {}
        if warnings:
            meta = attach_parser_warning(
                meta,
                parser=self,
                code="salvaged_json_payload",
                summary="Parser warnings were recorded while reading JSON decision output.",
                raw_output=raw_output,
                details="; ".join(warnings),
                expected_shape='{"thought":"...","action":{"name":"tool_name","args":{...}}} or {"thought":"...","final_answer":"..."}',
                extraction_mode=extraction_mode,
                salvage_applied=extraction_mode not in {"", "direct"},
                salvage_summary="; ".join(warnings),
            )
        final_answer = (
            first_dict_value(payload, self.final_keys)
            or first_dict_value(payload, ("final_answer",))
            or first_dict_value(payload, ("answer",))
        )

        if mode == "wait":
            return Decision.wait(rationale=thought, meta=meta)
        if mode == "final":
            if not final_answer:
                return parser_wait_decision(
                    parser=self,
                    code="missing_required_field",
                    summary="JSON final mode is missing final_answer.",
                    raw_output=raw_output,
                    details="The payload set mode='final' but did not provide final_answer or answer.",
                    repair_instruction="When mode is 'final', include `final_answer` as a string.",
                    expected_shape='{"mode":"final","thought":"...","final_answer":"..."}',
                    issue_path="final_answer",
                    rationale=thought or None,
                    extra_meta=meta,
                )
            return Decision.final(answer=final_answer, rationale=thought, meta=meta)

        actions = extract_json_actions(payload)
        if actions:
            return Decision.act(actions=actions, rationale=thought, meta=meta)
        if final_answer:
            return Decision.final(answer=final_answer, rationale=thought, meta=meta)
        return parser_wait_decision(
            parser=self,
            code="missing_action_or_final",
            summary="JSON output did not contain an action or final answer.",
            raw_output=raw_output,
            details="The parser did not find parseable action fields, actions, or a final answer.",
            repair_instruction='Return JSON with either an `action`, an `actions` array, a `final_answer`, or `mode: "wait"`.',
            expected_shape='{"thought":"...","action":{"name":"tool_name","args":{...}}} or {"mode":"final","final_answer":"..."}',
            rationale=thought or None,
            extra_meta=meta,
        )


__all__ = ["JsonDecisionParser"]
