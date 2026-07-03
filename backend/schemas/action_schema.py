from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

HIGH_LEVEL_ACTION_NAMES = (
    "observe",
    "move forward",
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
    "done": "end",
}


class ActionRequest(BaseModel):
    action: str
    thought: str | None = None


class HighLevelAction(BaseModel):
    name: Literal[
        "observe",
        "move forward",
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
    raw_text: str | None = None
    raw_json: dict[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_action_name(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        name = data.get("name")
        if isinstance(name, str):
            normalized = ACTION_NAME_ALIASES.get(name.strip().lower().replace("-", "_"))
            if normalized:
                data = dict(data)
                data["name"] = normalized
        return data
