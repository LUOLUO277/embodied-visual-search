from __future__ import annotations

from typing import Any


def _step(controller: Any, **payload: Any) -> Any:
    return controller.step(**payload)


def move_ahead(controller: Any, move_magnitude: float = 0.25) -> Any:
    return _step(controller, action="MoveAhead", moveMagnitude=move_magnitude)


def rotate_left(controller: Any, degrees: float = 90) -> Any:
    return _step(controller, action="RotateLeft", degrees=degrees)


def rotate_right(controller: Any, degrees: float = 90) -> Any:
    return _step(controller, action="RotateRight", degrees=degrees)


def teleport(controller: Any, position: dict[str, float], rotation: dict[str, float] | float, horizon: float = 60.0, standing: bool = True) -> Any:
    yaw = float(rotation if isinstance(rotation, (int, float)) else rotation.get("y", 0.0))
    return _step(
        controller,
        action="TeleportFull",
        x=float(position.get("x", 0.0)),
        y=float(position.get("y", 0.0)),
        z=float(position.get("z", 0.0)),
        rotation=yaw,
        horizon=float(horizon),
        standing=standing,
    )


def pickup(controller: Any, object_id: str) -> Any:
    return _step(controller, action="PickupObject", objectId=object_id)


def put_in(controller: Any, object_id: str) -> Any:
    return _step(controller, action="PutObject", objectId=object_id, placeStationary=True)


def open_object(controller: Any, object_id: str) -> Any:
    return _step(controller, action="OpenObject", objectId=object_id, openness=1.0)


def close_object(controller: Any, object_id: str) -> Any:
    return _step(controller, action="CloseObject", objectId=object_id)


def toggle(controller: Any, object_id: str, is_toggled: bool) -> Any:
    action_name = "ToggleObjectOff" if is_toggled else "ToggleObjectOn"
    return _step(controller, action=action_name, objectId=object_id)


def done(controller: Any) -> Any:
    return _step(controller, action="Done")
