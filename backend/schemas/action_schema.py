from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

HIGH_LEVEL_ACTION_NAMES = (
    "observe",
    "move forward",
    "move back",
    "move left",
    "move right",
    "rotate left",
    "rotate right",
    "look up",
    "look down",
    "navigate to",
    "pickup",
    "put in",
    "toggle",
    "open",
    "close",
    "end",
)

MAX_ACTION_REPETITIONS = 3

ACTION_NAME_ALIASES = {
    "navigate_to": "navigate to",
    "pickup_object": "pickup",
    "put_in": "put in",
    "put": "put in",
    "move_forward": "move forward",
    "move_back": "move back",
    "move_left": "move left",
    "move_right": "move right",
    "turn_left": "rotate left",
    "turn_right": "rotate right",
    "rotate_left": "rotate left",
    "rotate_right": "rotate right",
    "look_up": "look up",
    "look_down": "look down",
    "done": "end",
}

REPEATABLE_ACTIONS = {
    "move forward",
    "move back",
    "move left",
    "move right",
    "rotate left",
    "rotate right",
    "look up",
    "look down",
}

REPEATED_ACTION_PATTERN = re.compile(r"^(?P<name>.+?)(?:\s*[*xX]\s*)(?P<count>\d+)$")


class ActionRequest(BaseModel):
    action: str
    thought: str | None = None


class HighLevelAction(BaseModel):
    name: Literal[
        "observe",
        "move forward",
        "move back",
        "move left",
        "move right",
        "rotate left",
        "rotate right",
        "look up",
        "look down",
        "navigate to",
        "pickup",
        "put in",
        "toggle",
        "open",
        "close",
        "end",
    ]
    argument: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    repetitions: int = Field(default=1, ge=1, le=MAX_ACTION_REPETITIONS)
    raw_text: str | None = None
    raw_json: dict[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_action_name(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        normalized_data = dict(data)
        name = normalized_data.get("name")
        raw_repetition_requested = False
        if isinstance(name, str):
            stripped_name = name.strip()
            repeated_match = REPEATED_ACTION_PATTERN.match(stripped_name)
            if repeated_match:
                raw_repetition_requested = True
                stripped_name = repeated_match.group("name").strip()
                count = int(repeated_match.group("count"))
                normalized_data["repetitions"] = min(max(count, 1), MAX_ACTION_REPETITIONS)
            alias_key = stripped_name.lower().replace("-", "_").replace(" ", "_")
            normalized = ACTION_NAME_ALIASES.get(alias_key, stripped_name.lower())
            normalized_data["name"] = normalized
            if raw_repetition_requested and normalized not in REPEATABLE_ACTIONS:
                raise ValueError(f"Action '{normalized}' does not support repetitions.")
        repetitions = normalized_data.get("repetitions", 1)
        try:
            repetitions = int(repetitions)
        except (TypeError, ValueError):
            repetitions = 1
        normalized_data["repetitions"] = min(max(repetitions, 1), MAX_ACTION_REPETITIONS)
        return normalized_data
