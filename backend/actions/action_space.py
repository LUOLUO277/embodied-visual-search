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

MANUAL_ACTION_DISPLAY_NAMES = {
    ActionName.MOVE_AHEAD.value: "前进 - MoveAhead",
    ActionName.MOVE_BACK.value: "后退 - MoveBack",
    ActionName.MOVE_LEFT.value: "左移 - MoveLeft",
    ActionName.MOVE_RIGHT.value: "右移 - MoveRight",
    ActionName.ROTATE_LEFT.value: "左转 - RotateLeft",
    ActionName.ROTATE_RIGHT.value: "右转 - RotateRight",
    ActionName.LOOK_UP.value: "抬头 - LookUp",
    ActionName.LOOK_DOWN.value: "低头 - LookDown",
    ActionName.DONE.value: "结束 - Done",
}


def get_manual_action_metadata() -> list[dict[str, object]]:
    return [
        {
            "name": action,
            "display_name": MANUAL_ACTION_DISPLAY_NAMES.get(action, action),
            "requires_target": False,
            "supports_repetitions": False,
        }
        for action in MANUAL_ACTIONS
    ]
