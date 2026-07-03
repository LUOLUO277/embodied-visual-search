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

ACTION_NAME_ALIASES = {
    "navigate_to": "navigate to",
    "pickup_object": "pickup",
    "put_in": "put in",
    "put": "put in",
    "move_forward": "move forward",
    "move_back": "move back",
    "move_left": "move left",
    "move_right": "move right",
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
    repetitions: int = Field(default=1, ge=1, le=5)
    raw_text: str | None = None
    raw_json: dict[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_action_name(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        normalized_data = dict(data)
        name = normalized_data.get("name")
        if isinstance(name, str):
            stripped_name = name.strip()
            repeated_match = REPEATED_ACTION_PATTERN.match(stripped_name)
            if repeated_match:
                stripped_name = repeated_match.group("name").strip()
                normalized_data["repetitions"] = int(repeated_match.group("count"))
            alias_key = stripped_name.lower().replace("-", "_").replace(" ", "_")
            normalized = ACTION_NAME_ALIASES.get(alias_key, stripped_name.lower())
            normalized_data["name"] = normalized
            if normalized_data.get("repetitions", 1) > 1 and normalized not in REPEATABLE_ACTIONS:
                normalized_data["repetitions"] = 1
        return normalized_data
