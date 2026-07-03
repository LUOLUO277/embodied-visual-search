from __future__ import annotations

import json
from dataclasses import dataclass, field
from json import JSONDecodeError
from typing import Any

from pydantic import ValidationError

from backend.schemas.agent_schema import AgentActionResult, AgentThought, MemoryUpdate
from backend.schemas.action_schema import HighLevelAction

PHASES = {"initial_scan", "visual_search", "navigation", "interaction", "recovery", "completion_check"}


@dataclass
class ParsedAgentOutput:
    thought: AgentThought
    action: HighLevelAction
    raw_json: dict[str, Any]
    memory_update: MemoryUpdate = field(default_factory=MemoryUpdate)


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
        memory_update_payload = payload.get("memory_update") or {}
        if not isinstance(thought_payload, dict) or not isinstance(action_payload, dict):
            raise UnsupportedModelOutputError("Model output must contain object fields: thought and action.")
        if not isinstance(memory_update_payload, dict):
            memory_update_payload = {}
        action_payload = dict(action_payload)
        action_payload.setdefault("raw_json", payload)
        action_payload.setdefault("raw_text", raw_output)
        try:
            action = HighLevelAction.model_validate(action_payload)
            thought = AgentThought.model_validate(OutputParser._normalize_thought_payload(thought_payload, action))
            memory_update = MemoryUpdate.model_validate(OutputParser._normalize_memory_update(memory_update_payload))
        except ValidationError as exc:
            raise OutputParserError(str(exc)) from exc
        except ValueError as exc:
            raise OutputParserError(str(exc)) from exc
        return ParsedAgentOutput(thought=thought, action=action, raw_json=payload, memory_update=memory_update)

    @staticmethod
    def _normalize_thought_payload(thought_payload: dict[str, Any], action: HighLevelAction) -> dict[str, Any]:
        phase = OutputParser._clean_text(thought_payload.get("phase"))
        decision = OutputParser._clean_text(thought_payload.get("decision"))
        memory_reasoning = OutputParser._clean_text(thought_payload.get("memory_reasoning"))
        new_spatial = OutputParser._clean_text(thought_payload.get("spatial_reasoning"))
        new_verification = OutputParser._clean_text(thought_payload.get("verification"))
        new_situation = OutputParser._clean_text(thought_payload.get("situation_analysis"))

        if phase or decision or memory_reasoning:
            return {
                "phase": OutputParser._normalize_phase(phase, action=action),
                "situation_analysis": new_situation or decision or "",
                "spatial_reasoning": new_spatial,
                "memory_reasoning": memory_reasoning,
                "verification": new_verification,
                "decision": decision or new_situation or "",
            }

        brief = OutputParser._clean_text(thought_payload.get("brief"))
        modes_raw = thought_payload.get("modes")
        modes: list[str] = []
        if isinstance(modes_raw, str):
            modes_raw = [modes_raw]
        if isinstance(modes_raw, list):
            for item in modes_raw:
                cleaned = OutputParser._clean_text(item)
                if cleaned and cleaned not in modes:
                    modes.append(cleaned)
        if brief or modes:
            inferred_phase = OutputParser._infer_phase_from_modes(modes, action)
            return {
                "phase": inferred_phase,
                "situation_analysis": brief or "",
                "spatial_reasoning": brief if "spatial_reasoning" in modes else None,
                "memory_reasoning": brief if "self_reflection" in modes else None,
                "verification": brief if "verification" in modes else None,
                "decision": brief or "",
            }

        legacy_situation = OutputParser._clean_text(thought_payload.get("situation_analysis"))
        legacy_spatial = OutputParser._clean_text(thought_payload.get("spatial_reasoning"))
        legacy_plan = OutputParser._clean_text(thought_payload.get("task_planning"))
        legacy_reflection = OutputParser._clean_text(thought_payload.get("self_reflection"))
        legacy_verification = OutputParser._clean_text(thought_payload.get("verification"))
        legacy_phase = OutputParser._infer_phase_from_legacy(action, legacy_reflection, legacy_verification)
        decision_fallback = legacy_plan or legacy_situation or legacy_spatial or legacy_reflection or legacy_verification or ""
        return {
            "phase": legacy_phase,
            "situation_analysis": legacy_situation or decision_fallback,
            "spatial_reasoning": legacy_spatial,
            "memory_reasoning": legacy_reflection,
            "verification": legacy_verification,
            "decision": decision_fallback,
        }

    @staticmethod
    def _normalize_memory_update(memory_update_payload: dict[str, Any]) -> dict[str, Any]:
        checked = OutputParser._clean_text(memory_update_payload.get("checked"))
        ruled_out = OutputParser._clean_text(memory_update_payload.get("ruled_out"))
        clue = OutputParser._clean_text(memory_update_payload.get("clue"))
        avoid = OutputParser._clean_text(memory_update_payload.get("avoid"))

        if not checked:
            checked = (
                OutputParser._clean_text(memory_update_payload.get("searched_area"))
                or OutputParser._clean_text(memory_update_payload.get("observed_area"))
                or OutputParser._clean_text(memory_update_payload.get("negative_finding"))
            )
        if not ruled_out:
            ruled_out = OutputParser._clean_text(memory_update_payload.get("negative_finding"))
        if not clue:
            clue = (
                OutputParser._clean_text(memory_update_payload.get("positive_clue"))
                or OutputParser._clean_text(memory_update_payload.get("current_hypothesis"))
            )
        if not avoid:
            avoid = OutputParser._clean_text(memory_update_payload.get("negative_finding"))

        return {"checked": checked, "ruled_out": ruled_out, "clue": clue, "avoid": avoid}

    @staticmethod
    def _normalize_phase(phase: str | None, action: HighLevelAction) -> str:
        if phase in PHASES:
            return phase
        return OutputParser._infer_phase_from_action(action)

    @staticmethod
    def _infer_phase_from_modes(modes: list[str], action: HighLevelAction) -> str:
        if "self_reflection" in modes:
            return "recovery"
        if "verification" in modes and action.name in {"pickup", "end"}:
            return "completion_check"
        if not modes:
            return OutputParser._infer_phase_from_action(action)
        if "spatial_reasoning" in modes:
            return "navigation" if action.name in {"move forward", "move back", "move left", "move right", "rotate left", "rotate right", "look up", "look down", "navigate to", "observe"} else "visual_search"
        return "visual_search"

    @staticmethod
    def _infer_phase_from_legacy(action: HighLevelAction, legacy_reflection: str | None, legacy_verification: str | None) -> str:
        if legacy_reflection:
            return "recovery"
        if legacy_verification and action.name in {"pickup", "end"}:
            return "completion_check"
        return OutputParser._infer_phase_from_action(action)

    @staticmethod
    def _infer_phase_from_action(action: HighLevelAction) -> str:
        if action.name in {"move forward", "move back", "move left", "move right", "rotate left", "rotate right", "look up", "look down", "navigate to", "observe"}:
            return "navigation"
        if action.name in {"pickup", "put in", "toggle", "open", "close"}:
            return "interaction"
        if action.name == "end":
            return "completion_check"
        return "visual_search"

    @staticmethod
    def _clean_text(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        return cleaned or None

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
