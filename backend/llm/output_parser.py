from __future__ import annotations

import json
from dataclasses import dataclass

from backend.schemas.agent_schema import AgentActionResult, AgentThought
from backend.schemas.action_schema import HighLevelAction


@dataclass
class ParsedAgentOutput:
    thought: AgentThought
    action: HighLevelAction
    raw_json: dict


class OutputParserError(ValueError):
    pass


class UnsupportedModelOutputError(OutputParserError):
    pass


class OutputParser:
    @staticmethod
    def parse(raw_output: str) -> ParsedAgentOutput:
        payload = OutputParser._load_json(raw_output)
        thought_payload = payload.get("thought")
        action_payload = payload.get("action")
        if not isinstance(thought_payload, dict) or not isinstance(action_payload, dict):
            raise UnsupportedModelOutputError("Model output must contain object fields: thought and action.")
        action_payload = dict(action_payload)
        action_payload.setdefault("raw_json", payload)
        action_payload.setdefault("raw_text", raw_output)
        return ParsedAgentOutput(
            thought=AgentThought.model_validate(thought_payload),
            action=HighLevelAction.model_validate(action_payload),
            raw_json=payload,
        )

    @staticmethod
    def _load_json(raw_output: str) -> dict:
        candidates = [raw_output.strip()]
        fence = OutputParser._extract_fenced_json(raw_output)
        if fence:
            candidates.append(fence)
        inline = OutputParser._extract_first_json_object(raw_output)
        if inline:
            candidates.append(inline)

        for candidate in candidates:
            if not candidate:
                continue
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload
        raise OutputParserError("Failed to parse JSON from model output.")

    @staticmethod
    def _extract_fenced_json(raw_output: str) -> str | None:
        start_markers = ["```json", "```"]
        for marker in start_markers:
            start = raw_output.find(marker)
            if start == -1:
                continue
            start += len(marker)
            end = raw_output.find("```", start)
            if end == -1:
                continue
            return raw_output[start:end].strip()
        return None

    @staticmethod
    def _extract_first_json_object(raw_output: str) -> str | None:
        start = raw_output.find("{")
        if start == -1:
            return None
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(raw_output)):
            char = raw_output[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return raw_output[start : index + 1]
        return None


def build_parse_error_result(message: str) -> AgentActionResult:
    return AgentActionResult(
        success=False,
        action_name="observe",
        normalized_action="observe",
        message=message,
        error_type="parse_error",
        error=message,
        executed=False,
        done=False,
    )
