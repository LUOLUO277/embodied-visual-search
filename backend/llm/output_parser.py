from __future__ import annotations

import json
from dataclasses import dataclass, field
from json import JSONDecodeError
from typing import Any

from backend.schemas.agent_schema import AgentActionResult, AgentThought
from backend.schemas.action_schema import HighLevelAction


@dataclass
class ParsedAgentOutput:
    thought: AgentThought
    action: HighLevelAction
    raw_json: dict[str, Any]
    memory_update: dict[str, Any] = field(default_factory=dict)


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
        memory_update = payload.get("memory_update") or {}
        if not isinstance(memory_update, dict):
            memory_update = {}
        if not isinstance(thought_payload, dict) or not isinstance(action_payload, dict):
            raise UnsupportedModelOutputError("Model output must contain object fields: thought and action.")
        action_payload = dict(action_payload)
        action_payload.setdefault("raw_json", payload)
        action_payload.setdefault("raw_text", raw_output)
        return ParsedAgentOutput(
            thought=AgentThought.model_validate(thought_payload),
            action=HighLevelAction.model_validate(action_payload),
            raw_json=payload,
            memory_update=memory_update,
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
        repaired = OutputParser._repair_truncated_json(raw_output)
        if repaired:
            candidates.append(repaired)

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

    @staticmethod
    def _repair_truncated_json(raw_output: str) -> str | None:
        candidate = raw_output.strip()
        if not candidate:
            return None
        if "```" in candidate:
            fenced = OutputParser._extract_fenced_json(candidate)
            candidate = fenced or candidate
        start = candidate.find("{")
        if start == -1:
            return None
        candidate = candidate[start:]
        candidate = OutputParser._trim_incomplete_tail(candidate)
        candidate = OutputParser._balance_json(candidate)
        try:
            payload = json.loads(candidate)
        except JSONDecodeError:
            return None
        return candidate if isinstance(payload, dict) else None

    @staticmethod
    def _trim_incomplete_tail(candidate: str) -> str:
        trimmed = candidate.rstrip()
        previous = None
        while trimmed and trimmed != previous:
            previous = trimmed
            if trimmed.endswith(":"):
                key_start = trimmed.rfind('"')
                if key_start != -1:
                    key_start = trimmed.rfind('"', 0, key_start)
                comma_index = trimmed.rfind(",")
                if comma_index != -1 and comma_index > key_start:
                    trimmed = trimmed[:comma_index]
                elif key_start != -1:
                    trimmed = trimmed[:key_start]
                else:
                    trimmed = trimmed[:-1]
                trimmed = trimmed.rstrip()
                continue
            if trimmed.endswith(","):
                trimmed = trimmed[:-1].rstrip()
        return trimmed

    @staticmethod
    def _balance_json(candidate: str) -> str:
        stack: list[str] = []
        in_string = False
        escaped = False
        for char in candidate:
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
            elif char in "[{":
                stack.append("}" if char == "{" else "]")
            elif char in "}]" and stack and char == stack[-1]:
                stack.pop()
        repaired = candidate
        if in_string:
            repaired += '"'
        while stack:
            repaired += stack.pop()
        return repaired


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
