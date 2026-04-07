"""XML decision parser with configurable tag/keyword mapping."""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from qitos.core.decision import Decision
from qitos.engine.parser import BaseParser, parser_wait_decision
from qitos.kit.parser.parser_utils import (
    first_xml_text,
    norm,
    parse_xml_action,
    parse_xml_root,
)


class XmlDecisionParser(BaseParser[dict[str, Any]]):
    contract_id = "xml_decision_v1"

    def __init__(
        self,
        *,
        thought_keys: Optional[Sequence[str]] = None,
        reflection_keys: Optional[Sequence[str]] = None,
        action_keys: Optional[Sequence[str]] = None,
        final_keys: Optional[Sequence[str]] = None,
        xml_think_tags: Optional[Sequence[str]] = None,
        xml_reflection_tags: Optional[Sequence[str]] = None,
        xml_action_tags: Optional[Sequence[str]] = None,
        xml_final_tags: Optional[Sequence[str]] = None,
    ):
        # Keep text-style keys configurable for API symmetry, even if XML parsers
        # primarily rely on XML tags.
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
        self.xml_think_tags = tuple(
            norm(x)
            for x in (xml_think_tags or ("think", "thought", "thinking", "rationale"))
        )
        self.xml_reflection_tags = tuple(
            norm(x)
            for x in (
                xml_reflection_tags or ("reflection", "reflect", "self_reflection")
            )
        )
        self.xml_action_tags = tuple(
            norm(x) for x in (xml_action_tags or ("action", "tool", "call"))
        )
        self.xml_final_tags = tuple(
            norm(x) for x in (xml_final_tags or ("final_answer", "final", "answer"))
        )

    def parse(
        self, raw_output: Any, context: Optional[Dict[str, Any]] = None
    ) -> Decision[dict[str, Any]]:
        if not isinstance(raw_output, str):
            return parser_wait_decision(
                parser=self,
                code="invalid_output_type",
                summary="Expected XML string output for XML decision parsing.",
                raw_output=raw_output,
                details="XmlDecisionParser expects a string response.",
                repair_instruction="Return XML only, with either an action tag or a final answer tag.",
                expected_shape='<decision mode="act"><think>...</think><action name="tool_name">...</action></decision>',
            )
        text = raw_output.strip()
        if not text:
            return parser_wait_decision(
                parser=self,
                code="empty_output",
                summary="Model output was empty.",
                raw_output=raw_output,
                details="The response did not contain any XML to parse.",
                repair_instruction="Return XML only, with either an action tag or a final answer tag.",
                expected_shape='<decision mode="act"><think>...</think><action name="tool_name">...</action></decision>',
            )

        try:
            root = parse_xml_root(text)
        except Exception as exc:
            return parser_wait_decision(
                parser=self,
                code="invalid_xml",
                summary="Could not parse a valid XML decision payload.",
                raw_output=raw_output,
                details=str(exc),
                repair_instruction="Return well-formed XML only, with either an action tag or a final answer tag.",
                expected_shape='<decision mode="act"><think>...</think><action name="tool_name">...</action></decision>',
            )
        mode = norm(root.attrib.get("mode", "")) if hasattr(root, "attrib") else ""
        thought = first_xml_text(root, self.xml_think_tags)
        reflection = first_xml_text(root, self.xml_reflection_tags)
        final_answer = first_xml_text(root, self.xml_final_tags)
        meta = {"reflection": reflection} if reflection else {}

        if mode == "wait":
            return Decision.wait(rationale=thought, meta=meta)
        if mode == "final":
            if not final_answer:
                return parser_wait_decision(
                    parser=self,
                    code="missing_required_field",
                    summary="XML final mode is missing final answer content.",
                    raw_output=raw_output,
                    details="The payload set mode='final' but did not include final answer text.",
                    repair_instruction="When mode is 'final', include text inside a final answer tag such as <final_answer>...</final_answer>.",
                    expected_shape='<decision mode="final"><think>...</think><final_answer>...</final_answer></decision>',
                    issue_path="final_answer",
                    rationale=thought or None,
                    extra_meta=meta,
                )
            return Decision.final(answer=final_answer, rationale=thought, meta=meta)
        if mode == "act":
            action = parse_xml_action(root, self.xml_action_tags)
            if action is None:
                return parser_wait_decision(
                    parser=self,
                    code="invalid_action_schema",
                    summary="XML act mode is missing a parseable action.",
                    raw_output=raw_output,
                    details="The payload set mode='act' but the action block could not be parsed.",
                    repair_instruction='When mode is \'act\', include a valid action such as <action name="tool_name"><arg name="key">value</arg></action>.',
                    expected_shape='<decision mode="act"><think>...</think><action name="tool_name"><arg name="key">value</arg></action></decision>',
                    rationale=thought or None,
                    extra_meta=meta,
                )
            return Decision.act(actions=[action], rationale=thought, meta=meta)

        if final_answer:
            return Decision.final(answer=final_answer, rationale=thought, meta=meta)
        action = parse_xml_action(root, self.xml_action_tags)
        if action is not None:
            return Decision.act(actions=[action], rationale=thought, meta=meta)
        return parser_wait_decision(
            parser=self,
            code="missing_action_or_final",
            summary="XML output did not contain a parseable action or final answer.",
            raw_output=raw_output,
            details="The parser could not find either a valid action block or final answer content.",
            repair_instruction="Return XML with either a parseable action block or a final answer block.",
            expected_shape='<decision><think>...</think><action name="tool_name">...</action></decision> or <decision><final_answer>...</final_answer></decision>',
            rationale=thought or None,
            extra_meta=meta,
        )


__all__ = ["XmlDecisionParser"]
