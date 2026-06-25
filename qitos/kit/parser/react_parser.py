"""ReAct-style text parser with configurable keyword mapping."""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from qitos.core.decision import Decision
from qitos.engine.parser import BaseParser, parser_wait_decision
from qitos.kit.parser.parser_utils import (
    extract_labeled_blocks,
    first_block_value,
    first_xml_text,
    norm,
    parse_action_any,
    parse_xml_action,
    parse_xml_root,
)


class ReActTextParser(BaseParser[dict[str, Any]]):
    contract_id = "react_text_v1"

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
        if not isinstance(raw_output, str):
            return parser_wait_decision(
                parser=self,
                code="invalid_output_type",
                summary="Expected plain text output for ReAct parsing.",
                raw_output=raw_output,
                details="ReActTextParser expects a string model response.",
                repair_instruction="Return plain text with either `Action:` or `Final Answer:` in the required ReAct format.",
                expected_shape="Thought: ...\\nAction: tool(arg=value)  or  Final Answer: ...",
            )
        text = raw_output.strip()
        if not text:
            return parser_wait_decision(
                parser=self,
                code="empty_output",
                summary="Model output was empty.",
                raw_output=raw_output,
                details="The response did not contain any ReAct content to parse.",
                repair_instruction="Return a non-empty ReAct response with either `Action:` or `Final Answer:`.",
                expected_shape="Thought: ...\\nAction: tool(arg=value)  or  Final Answer: ...",
            )

        blocks = extract_labeled_blocks(text)
        thought = first_block_value(blocks, self.thought_keys)
        reflection = first_block_value(blocks, self.reflection_keys)
        final_answer = first_block_value(blocks, self.final_keys)
        action_blob = first_block_value(blocks, self.action_keys)

        meta = {"reflection": reflection} if reflection else {}
        if final_answer:
            return Decision.final(answer=final_answer, rationale=thought, meta=meta)

        if "<" in text and ">" in text:
            try:
                root = parse_xml_root(text)
            except Exception:
                root = None
            if root is not None:
                xml_thought = thought or first_xml_text(root, self.thought_keys)
                xml_reflection = reflection or first_xml_text(
                    root, self.reflection_keys
                )
                xml_meta = {"reflection": xml_reflection} if xml_reflection else {}
                xml_final = first_xml_text(root, self.final_keys)
                if xml_final:
                    return Decision.final(
                        answer=xml_final, rationale=xml_thought, meta=xml_meta
                    )
                xml_action = parse_xml_action(root, self.action_keys)
                if xml_action is not None:
                    return Decision.act(
                        actions=[xml_action], rationale=xml_thought, meta=xml_meta
                    )

        action = parse_action_any(text)
        if action is None and action_blob:
            action = parse_action_any(action_blob)
        if action is not None:
            return Decision.act(actions=[action], rationale=thought, meta=meta)
        return parser_wait_decision(
            parser=self,
            code="missing_action_or_final",
            summary="No ReAct action or final answer was found.",
            raw_output=raw_output,
            details="The response did not include a parseable `Action:` block or a `Final Answer:` block.",
            repair_instruction="Return a valid ReAct response with either `Action: tool_name(arg=value, ...)` or `Final Answer: ...`.",
            expected_shape="Thought: ...\\nAction: tool(arg=value)  or  Final Answer: ...",
            rationale=thought or None,
            extra_meta=meta,
        )


__all__ = ["ReActTextParser"]
