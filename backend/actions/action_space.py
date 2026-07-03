from __future__ import annotations

from enum import Enum


class ActionName(str, Enum):
    MOVE_AHEAD = "MoveAhead"
    MOVE_BACK = "MoveBack"
    MOVE_LEFT = "MoveLeft"
    MOVE_RIGHT = "MoveRight"
    ROTATE_LEFT = "RotateLeft"
    ROTATE_RIGHT = "RotateRight"
    LOOK_UP = "LookUp"
    LOOK_DOWN = "LookDown"
    DONE = "Done"


HIGH_LEVEL_ACTIONS = [
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

MANUAL_ACTIONS = [action.value for action in ActionName]
SUPPORTED_ACTIONS = MANUAL_ACTIONS
