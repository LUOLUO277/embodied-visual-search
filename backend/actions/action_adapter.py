from __future__ import annotations

from backend.actions.action_space import ActionName

ACTION_PAYLOADS = {
    ActionName.MOVE_AHEAD.value: {"action": "MoveAhead", "moveMagnitude": 0.25},
    ActionName.MOVE_BACK.value: {"action": "MoveBack", "moveMagnitude": 0.25},
    ActionName.MOVE_LEFT.value: {"action": "MoveLeft", "moveMagnitude": 0.25},
    ActionName.MOVE_RIGHT.value: {"action": "MoveRight", "moveMagnitude": 0.25},
    ActionName.ROTATE_LEFT.value: {"action": "RotateLeft", "degrees": 30},
    ActionName.ROTATE_RIGHT.value: {"action": "RotateRight", "degrees": 30},
    ActionName.LOOK_UP.value: {"action": "LookUp", "degrees": 15},
    ActionName.LOOK_DOWN.value: {"action": "LookDown", "degrees": 15},
    ActionName.DONE.value: {"action": "Done"},
}


def get_action_payload(action_name: str) -> dict:
    if action_name not in ACTION_PAYLOADS:
        raise ValueError(f"Unsupported action: {action_name}")
    return ACTION_PAYLOADS[action_name]
